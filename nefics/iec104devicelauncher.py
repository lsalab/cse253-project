#!/usr/bin/env python3

import os
import sys
import signal
from time import sleep
from datetime import datetime
from threading import Thread
from types import FrameType
from socket import SHUT_RDWR, socket, timeout, AF_INET, SOCK_STREAM, IPPROTO_TCP
from Crypto.Random.random import randint

# NEFICS imports
from nefics.modules.devicebase import IEDBase
from nefics.IEC104.dissector import APDU, APCI, ASDU

IEC104_T1 = 15
IEC104_PORT = 2404
IEC104_BUFFER_SIZE = 65536 # 64K

class IEC104Device(Thread):

    def __init__(self, device: IEDBase):
        super().__init__()
        self._terminate = False
        self._device = device
        self._connections = []
        self._data_transfer_status = {}
    
    def __str__(self) -> str:
        iecstr = f'### IEC-104 Simulated device\r\n'
        iecstr += f' ## Class: {self._device.__class__.__name__}\r\n'
        iecstr == f'  # Status at: {datetime.now().ctime()}\r\n'
        iecstr += f'----------------------------\r\n'
        iecstr += str(self._device)
        iecstr += f'----------------------------'
        return iecstr

    @property
    def terminate(self) -> bool:
        return self._terminate
    
    @terminate.setter
    def terminate(self, value: bool):
        self._terminate = value
    
    def set_terminate(self, signum: int, stack_frame: FrameType):
        if signum in [signal.SIGINT, signal.SIGTERM]:
            self._device.terminate = True
            self._terminate = True
            sys.stderr.write(f'Received a termination signal. Terminating threads ...\r\n')
            sys.stderr.flush()
        else:
            sys.stderr.write(f'Signal handler recevied an unsupported signal: {signum}\r\n')
            sys.stderr.flush()
    
    def status(self):
        stat = '\r\n\r\n'
        stat += str(self)
        print(stat)

    def _data_transfer(self, isock:socket, connid: int):
        '''
        This method is meant to be executed within a thread. It handles the
        data transfer loop of the simulated device. Each iteration requests
        the values to be sent, and sends one value each second while in a
        STARTED connection.
        '''
        while self._data_transfer_status[connid] and not self._terminate:
            values = self._device.poll_values_IEC104()
            for apdu in values:
                isock.send(apdu.build())
                sleep(1)

    def _connection_loop(self, isock: socket):
        connection_id = randint(0, 65535)
        while connection_id in self._data_transfer_status.keys():
            connection_id = randint(0, 65535)
        datatransfer:Thread = None
        self._data_transfer_status[connection_id] = False
        keepconn = True
        while keepconn and not self._terminate:
            try:
                data = isock.recv(IEC104_BUFFER_SIZE)
                data = APDU(data)
                frame_type = data['APCI'].Type
                if datatransfer is None:
                    # STOPPED connection
                    if frame_type in [0x00, 0x01]:
                        # I-Frame (0x00) OR S-Frame (0x01)
                        keepconn = False
                    else:
                        # U-Frame (0x03)
                        confirmation = APDU()/APCI(
                            ApduLen=4,
                            Type=0x03,
                            UType=data['APCI'].UType << 1
                        )
                        isock.send(confirmation.build())
                        if data['APCI'].UType == 0x01:
                            # STARTDT
                            self._data_transfer_status[connection_id] = True
                            datatransfer = Thread(target=self._data_transfer, args=[isock, connection_id])
                            datatransfer.start()
                else:
                    # STARTED connection
                    if frame_type == 0x00:
                        # I-Frame
                        apdu = self._device.handle_IEC104_IFrame(data)
                    elif frame_type == 0x01:
                        # S-Frame
                        self._device.tx = data['APCI'].Rx
                        apdu = None
                    else:
                        # U-Frame
                        apdu = APDU()/APCI(
                            ApduLen=4,
                            Type=0x03,
                            UType=data['APCI'].UType << 1
                        )
                        if data['APCI'].UType == 0x04:
                            # STOPDT
                            self._data_transfer_status[connection_id] = False
                            datatransfer.join()
                            # This join() is essentially the UNCONFIRMED STOPPED connection state
                            # the difference is that no incoming frames are received until the remaining
                            # data values are transfered to the controller.
                            datatransfer = None
                    if apdu is not None:
                        isock.send(apdu.build())
            except (timeout, BrokenPipeError) as ex:
                keepconn = False
        if datatransfer is not None:
            self._data_transfer_status[connection_id] = False
            datatransfer.join()
        isock.close()
        isock.shutdown(SHUT_RDWR)

    def run(self):
        listening_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        listening_sock.bind(('', IEC104_PORT))
        listening_sock.settimeout(2)
        self._device.start()
        while not self._terminate:
            try:
                incoming = listening_sock.accept(1)
                incoming.settimeout(IEC104_T1)
                new_conn = Thread(target=self._connection_loop, args=[incoming])
                self._connections.append(new_conn)
                new_conn.start()
            except timeout:
                pass
        while any(thr.is_alive() for thr in self._connections):
            for thr in self._connections:
                thr.join(1)
        self._device.join()
        listening_sock.close()
        listening_sock.shutdown(SHUT_RDWR)

def iec104_main():
    from importlib import import_module
    import io
    import argparse
    import json
    # Acquire configuration values for the device
    aparser = argparse.ArgumentParser(description='NEFICS IEC-104 Simulated device launcher')
    agr = aparser.add_mutually_exclusive_group(required=True)
    agr.add_argument('-c','--configfile', dest='config', type=argparse.FileType('r', encoding='UTF-8'))
    agr.add_argument('-C','--configstr', dest='config', type=str)
    args = aparser.parse_args()
    configarg = args.config
    if isinstance(configarg, io.TextIOWrapper):
        config = json.load(configarg)
        configarg.close()
    else:
        try:
            config = json.loads(configarg)
        except json.decoder.JSONDecodeError:
            sys.stderr.write(f'{configarg} is not a valid JSON string\r\n')
            sys.stderr.flush()
            sys.exit()
    # Assert whether the provided configuration has the minimum values
    try:
        required_values = ['module', 'class', 'guid', 'in', 'out', 'parameters']
        assert all(x in config.keys() for x in required_values)
    except AssertionError:
        sys.stderr.write(f'Corrupt configuration detected. Missing values: {", ".join([x for x in required_values if x not in config.keys()])}\r\n')
        sys.stderr.flush()
        sys.exit()
    # Assert whether the provided values are correctly typed
    try:
        assert all(isinstance(x, str) for x in [config['module'], config['class']])
        assert all(isinstance(x, list) for x in [config['in'], config['out']])
        assert all(isinstance(x, int) for x in [config['guid']] + config['in'] + config['out'])
    except AssertionError:
        sys.stderr.write(f'Type mismatch detected within the provided configuration\r\n')
        sys.stderr.flush()
        sys.exit()
    # Try to import the specified device module
    try:
        device_module = import_module(f'nefics.modules.{config["module"]}')
    except ModuleNotFoundError:
        sys.stderr.write(f'Could not find module "nefics.modules.{config["module"]}"\r\n')
        sys.stderr.flush()
        sys.exit()
    # Try to get the configured class from the specified module
    try:
        device_class = getattr(device_module, config['class'])
    except AttributeError:
        sys.stderr.write(f'Could not find class "{config["class"]}" in module "nefics.modules.{config["module"]}"\r\n')
        sys.stderr.flush()
        sys.exit()
    # Instantiate the device and assert whether it is compatible (devicebase.IEDBase)
    device = device_class(config['guid'], config['in'], config['out'], **config['parameters'])
    try:
        assert isinstance(device, IEDBase)
    except AssertionError:
        sys.stderr.write(f'Instantiated device ({device_class.__name__}) is not supported by NEFICS as a valid IEC-104 device\r\n')
        sys.stderr.flush()
        sys.exit()
    iec104 = IEC104Device(device)
    signal.signal(signal.SIGINT, iec104.set_terminate)
    signal.signal(signal.SIGTERM, iec104.set_terminate)

    def clearscreen():
        if os.name == 'nt':
            _ = os.system('cls')
        else:
            _ = os.system('clear')
    
    iec104.start()
    while not iec104.terminate:
        clearscreen()
        iec104.status()
        sleep(10)
    iec104.join()
    
if __name__ == '__main__':
    iec104_main()
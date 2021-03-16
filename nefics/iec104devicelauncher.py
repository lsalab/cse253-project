#!/usr/bin/env python3

import os
import sys
import signal
from time import sleep
from datetime import datetime
from threading import Thread
from types import FrameType

# NEFICS imports
from nefics.modules.devicebase import IEDBase

class IEC104Device(Thread):

    def __init__(self, device: IEDBase):
        super().__init__()
        self._terminate = False
        self._device = device
    
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
    
    def run(self):
        self._device.start()
        while not self._terminate:
            sleep(5)
        self._device.join()

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
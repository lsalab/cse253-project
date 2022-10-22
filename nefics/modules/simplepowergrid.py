#!/usr/bin/env python3
'''
This module implements three types of devices in a simple resistive powergrid.

Each device can have at most two physical neighbors (One input, one output).

The powergrid topology is a simple resistive powergrid comprised of a power
source, transmission substations, and a consumer load.

The source acts as the generator and is linked to one transmission substation.

A transmission substation has a input neighbor, which provides the input voltage;
and an output neighbor, to which the output voltage is supplied..

The consumer load has one transmission substation as its input.
'''

import signal
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket, timeout
import sys
from threading import Thread
from time import sleep
from types import FrameType
from Crypto.Random.random import randint

# NEFICS imports
from nefics.IEC104.dissector import *
from nefics.IEC104.ioa import *
import nefics.modules.devicebase as devicebase
import nefics.simproto as simproto

BASE_IOA = 1001

IEC104_T1 = 15
IEC104_PORT = 2404
IEC104_BUFFER_SIZE = 65536 # 64K

class IEC104DeviceHandler(Thread):

    def __init__(self, device: devicebase.IEDBase):
        super().__init__()
        self._terminate = False
        self._device = device
        self._connections = []
        self._data_transfer_status = {}
    
    def __str__(self) -> str:
        iecstr = f'### IEC-104 Simulated device\r\n'
        iecstr += f' ## Class: {self._device.__class__.__name__}\r\n'
        iecstr += f'  # Status at: {datetime.now().ctime()}\r\n'
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
                if len(data) > 0:
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
                                # data values are transferred to the controller.
                                datatransfer = None
                        if apdu is not None:
                            isock.send(apdu.build())
            except (timeout, BrokenPipeError) as ex:
                keepconn = False
        if datatransfer is not None:
            self._data_transfer_status[connection_id] = False
            datatransfer.join()
        isock.close()

    def run(self):
        listening_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        listening_sock.bind(('', IEC104_PORT))
        listening_sock.settimeout(2)
        listening_sock.listen()
        self._device.start()
        while not self._terminate:
            try:
                incoming, iaddr = listening_sock.accept()
                incoming.settimeout(IEC104_T1)
                new_conn = Thread(target=self._connection_loop, args=[incoming])
                self._connections.append(new_conn)
                new_conn.start()
            except timeout:
                continue
        while any(thr.is_alive() for thr in self._connections):
            for thr in self._connections:
                thr.join(1)
        self._device.join()
        listening_sock.close()

class Source(devicebase.IEDBase):
    '''
    Source device.

    Only needs to answer for the supplied voltage.

    For any incomming NEFICS requests, it will only answer to its neighbor.

    The value polling returns a single APDU with a type 36 (M_ME_TF_1) ASDU
    containing the voltage.
    '''

    def __init__(self, guid, neighbors_in=list(), neighbors_out=list(), **kwargs):
        assert all(val is not None for val in [guid, neighbors_out])
        assert all(isinstance(val, int) for val in neighbors_out)
        assert len(neighbors_out) >= 1
        assert 'voltage' in kwargs.keys()
        assert isinstance(kwargs['voltage'], float)
        super().__init__(guid, neighbors_in=[], neighbors_out=neighbors_out[:1], **kwargs)
        self._voltage = kwargs['voltage']
    
    def __str__(self) -> str:
        return f'Vout: {self._voltage:6.3f} V\r\n'
    
    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID in self._n_out_addr.keys():
            addr = self._n_out_addr[message.SenderID]
            if addr is not None:
                if message.MessageID == simproto.MESSAGE_ID['MSG_GETV']:
                    pkt = simproto.NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID=simproto.MESSAGE_ID['MSG_VOLT'],
                        FloatArg0=self._voltage
                    )
                else:
                    self._log(f'Received a NEFICS message not supported by simplepowergrid.Source from {addr}: {repr(message)}')
                    pkt = simproto.NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID=simproto.MESSAGE_ID['MSG_UKWN']
                    )
                self._sock.sendto(pkt.build(), addr)
    
    def poll_values_IEC104(self):
        ioa = IOA36(IOA=BASE_IOA, Value=self._voltage, QDS=0, CP56Time=devicebase.cp56time())
        pkt = APDU()
        pkt /= APCI(ApduLen=25, Type=0x00, Tx=self.tx, Rx=self.rx)
        pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
        self.tx += 1
        return [pkt]

    def handle_IEC104_IFrame(self, packet: APDU) -> APDU:
        # A source device shouldn't receive any I-Frames
        assert packet.haslayer('APCI')
        assert packet.haslayer('ASDU')
        apci:APCI = packet['APCI']
        self.tx = apci.Tx + 1
        self.rx = apci.Rx + 1
        response:APDU = packet
        response['APCI'].Rx = self.rx
        response['APCI'].Tx = self.tx
        response['ASDU'].CauseTx = 45 # Unknown CoT
        return response

class Transmission(devicebase.IEDBase):
    '''
    Transmission substation device.

    Emulates the behavior of a simple IED in a substation.

    The value polling returns two type 36 (M_ME_TF_1) ASDU containing the voltage and current values,
    and several type 3 (M_DP_NA_1) containing the status of each configured breaker.
    '''

    def __init__(self, guid: int, neighbors_in: list, neighbors_out: list, **kwargs):
        assert all(x is not None for x in [guid, neighbors_in, neighbors_out])
        assert all(isinstance(x, int) for x in neighbors_in + neighbors_out)
        assert len(neighbors_in) >= 1
        assert len(neighbors_out) >= 1
        assert all(x not in neighbors_out for x in neighbors_in)
        assert all(x in kwargs.keys() for x in ['loads', 'state'])
        assert isinstance(kwargs['loads'], list)
        assert all(isinstance(x, float) for x in kwargs['loads'])
        assert isinstance(kwargs['state'], int)
        assert kwargs['state'] in range(2**len(kwargs['loads']))
        super().__init__(guid, neighbors_in=neighbors_in, neighbors_out=neighbors_out, **kwargs)
        self._loads = kwargs['loads']
        self._state = kwargs['state']
        self._laststate = None
        self._load:float = None
        self._vin:float = None
        self._vout:float = None
        self._amp:float = None
        self._rload:float = None
        self._wait_exec = None
    
    def __str__(self) -> str:
        if all(x is not None for x in [self._vin, self._vout, self._amp, self._load, self._rload]):
            return f'Vin:  {self._vin:6.3f} V\r\nVout: {self._vout:6.3f} V\r\nI:    {self._amp:6.3f} A\r\nBreakers: {self._state:b}\r\nR:    {self._load:6.3f} Ohm\r\nLoad: {self._rload:6.3f} Ohm\r\n'
        return 'Awaiting data from configured neighbors ...\r\n'

    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID in list(self._n_in_addr.keys()) + list(self._n_out_addr.keys()):
            addr = self._n_in_addr[message.SenderID] if message.SenderID in self._n_in_addr.keys() else self._n_out_addr[message.SenderID]
            isinput = bool(message.SenderID in self._n_in_addr.keys())
            if addr is not None:
                pkt = simproto.NEFICSMSG(
                    SenderID=self.guid,
                    ReceiverID=message.SenderID,
                )
                if message.MessageID == simproto.MESSAGE_ID['MSG_GETV'] and not isinput:
                    if self._vout is not None:
                        pkt.MessageID = simproto.MESSAGE_ID['MSG_VOLT']
                        pkt.FloatArg0 = self._vout
                    else:
                        pkt.MessageID = simproto.MESSAGE_ID['MSG_NRDY']
                elif message.MessageID == simproto.MESSAGE_ID['MSG_VOLT'] and isinput:
                    self._vin = message.FloatArg0
                    pkt = None
                elif message.MessageID == simproto.MESSAGE_ID['MSG_GREQ'] and isinput:
                    if all(x is not None for x in [self._load, self._rload]):
                        pkt.MessageID = simproto.MESSAGE_ID['MSG_TREQ']
                        pkt.FloatArg0 = self._load + self._rload
                    else:
                        pkt.MessageID = simproto.MESSAGE_ID['MSG_NRDY']
                elif message.MessageID == simproto.MESSAGE_ID['MSG_TREQ'] and not isinput:
                    self._rload = message.FloatArg0
                    self._log(f'Received REQ {self._rload:f} from {addr[0]:s}')
                    return
                else:
                    self._log(f'Received a NEFICS message not supported by simplepowergrid.Transmission from {addr[0]}: {repr(message)}')
                    pkt.MessageID = simproto.MESSAGE_ID['MSG_UKWN']
                if pkt is not None:
                    self._sock.sendto(pkt.build(), addr)

    def simulate(self):
        # Request updated values
        if all(x is not None for x in list(self._n_in_addr.values()) + list(self._n_out_addr.values())):
            addrs = []
            pkts = []
            # Request output load
            dstid = list(self._n_out_addr.keys())[0]
            addrs.append(self._n_out_addr[dstid])
            pkts.append(simproto.NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=dstid,
                MessageID=simproto.MESSAGE_ID['MSG_GREQ']
            ))
            # Request input voltage
            dstid = list(self._n_in_addr.keys())[0]
            addrs.append(self._n_in_addr[dstid])
            pkts.append(simproto.NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=dstid,
                MessageID=simproto.MESSAGE_ID['MSG_GETV']
            ))
            # Send requests
            for pkt, addr in zip(pkts, addrs):
                self._sock.sendto(pkt.build(), addr)
            sleep(0.5)
        # Check for any state changes in the substation
        if self._state != self._laststate:
            self._laststate = self._state
            if self._state == 0:
                self._log('All breakers are OPEN', devicebase.LOG_PRIO['WARNING'])
                self._load = float('inf')
            else:
                self._load = None
                for i in range(len(self._loads)):       # Iterate over substation breakers
                    if (self._state & (2 ** i)) > 0:    # If the current breaker is 'OFF/CLOSED' ==> Corresponding load is connected
                        if self._loads[i] == 0:         # Failure condition ==> Simulate a broken breaker
                            #TODO: Failure condition
                            self._log(f'Failure condition: short circuit detected on breaker {(BASE_IOA // 10) + 1 +i}', devicebase.LOG_PRIO['CRITICAL'])
                            self._load = 0
                            break
                        else:
                            self._load = self._loads[i] if self._load is None else (self._load * self._loads[i]) / (self._load + self._loads[i])
        # Determine new local values
        if self._load == float('inf'):                  # Failure condition ==> No output, no current
            self._vout = 0
            self._amp = 0
        elif all(x is not None for x in [self._vin, self._load, self._rload]):
            if self._rload == float('inf'):             # Failure in another substation
                self._log('Breakers OPEN somewhere on the grid', devicebase.LOG_PRIO['WARNING'])
                self._vout = self._vin
            else:
                self._vout = self._vin * self._rload / (self._rload + self._load)
            try:
                self._amp = (self._vin - self._vout) / self._load
            except ZeroDivisionError:
                self._log('Short circuit somewhere on the grid', devicebase.LOG_PRIO['CRITICAL'])
                self._amp = float('inf')                # Failure condition - Short circuit in the system ==> Current increases toward infinity
        sleep(0.333)

    def poll_values_IEC104(self) -> list:
        iframes = []
        if all(x is not None for x in [self._vin, self._amp] + self._loads):
            # Input voltage
            ioa = IOA36(IOA=BASE_IOA, Value=self._vin, QDS=0, CP56Time=devicebase.cp56time())
            pkt = APDU()
            pkt /= APCI(ApduLen=25, Type=0x00, Tx=self.tx, Rx=self.rx)
            pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
            self.tx += 1
            iframes.append(pkt)
            # Measured current
            ioa = IOA36(IOA=BASE_IOA + 1, Value=self._amp, QDS=0, CP56Time=devicebase.cp56time())
            pkt = APDU()
            pkt /= APCI(ApduLen=25, Type=0x00, Tx=self.tx, Rx=self.rx)
            pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
            self.tx += 1
            iframes.append(pkt)
            # Breaker status
            for i in range(len(self._loads)):
                brvalue = 0x01 if (self._state & (2 ** i)) > 0 else 0x02
                ioa = IOA3(IOA=(BASE_IOA // 10) + i + 1, DIQ=DIQ(DPI=brvalue, flags=0x00))
                pkt = APDU()
                pkt /= APCI(ApduLen=14, Type=0x00, Tx=self.tx, Rx=self.rx)
                pkt /= ASDU(TypeId=3, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
                self.tx += 1
                iframes.append(pkt)
        return iframes
    
    def handle_IEC104_IFrame(self, packet: APDU) -> APDU:
        assert packet.haslayer('APCI')
        assert packet.haslayer('ASDU')
        apci:APCI = packet['APCI']
        asdu:ASDU = packet['ASDU']
        response:APDU = None
        if asdu.TypeId == 45:
            # Type 45: C_SC_NA_1 (Single command) -- 60870-5-101 IEC:2003 Section 7.3.2.1
            ioa:IOA45 = asdu['IOA45']
            self.tx = apci.Tx + 1
            self.rx = apci.Rx + 1
            response = APDU()
            response /= APCI(ApduLen=14, Type=0x00, Tx=self.tx, Rx=self.rx)
            if self._wait_exec is None and ioa.SCO.SE == 1 and asdu.CauseTx == 6:
                # SCO: Select; CoT: Act
                if ioa.IOA in [(BASE_IOA // 10) + 1 + i for i in range(len(self._loads))]:
                    # SCO: Select; CoT: ActCon
                    self._wait_exec = ioa.IOA
                    response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=7, Test=0, OA=0, Addr=self.guid, IOA=ioa)
                else:
                    # SCO: Select; CoT: Unknown IOA
                    self._log(f'Received ASDU type 45 SELECT using an unknown IOA: {repr(packet)}', devicebase.LOG_PRIO['WARNING'])
                    response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=47, Test=0, OA=0, Addr=self.guid, IOA=ioa)
            elif self._wait_exec is not None and ioa.SCO.SE == 0 and asdu.CauseTx == 6:
                # SCO: Execute; CoT: Act
                if self._wait_exec == ioa.IOA:
                    # SCO: Execute; CoT: ActCon
                    response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=7, Test=0, OA=0, Addr=self.guid, IOA=ioa)
                    self._wait_exec = None
                    if bool(ioa.SCO.SCS):
                        # STATE OR IOA
                        self._state = self._state | (ioa.IOA - 1 - (BASE_IOA // 10))
                    else:
                        # STATE AND (IOA XOR 1...11)
                        self._state = self._state & ((ioa.IOA - 1 - (BASE_IOA // 10)) ^ ((2 ** len(self._loads)) - 1))
                else:
                    # SCO: Execute; CoT: Unknown IOA
                    self._log(f'Received ASDU type 45 EXECUTE using an unexpected IOA: {repr(packet)}', devicebase.LOG_PRIO['WARNING'])
                    response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=47, Test=0, OA=0, Addr=self.guid, IOA=ioa)
            elif self._wait_exec is not None and ioa.SCO.SE == 1 and asdu.CauseTx == 8:
                # SCO: Select; CoT: Deact
                # Reply -- SCO: Select; CoT: DeactCon
                self._wait_exec = None
                response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=9, Test=0, OA=0, Addr=self.guid, IOA=ioa)
            else:
                # CoT: Unknown CoT
                self._log(f'Received an unexpected ASDU type 45: {repr(packet)}', devicebase.LOG_PRIO['WARNING'])
                response /= ASDU(TypeId=45, SQ=0, NumIx=1, CauseTx=45, Test=0, OA=0, Addr=self.guid, IOA=ioa)
        if response is None:
            self._log(f'Received an unexpected I-Frame: {repr(packet)}', devicebase.LOG_PRIO['WARNING'])
            response = packet
            response['APCI'].Rx = self.rx
            response['APCI'].Tx = self.tx
            response['ASDU'].CauseTx = 45 # Unknown CoT
        return response

class Load(devicebase.IEDBase):
    '''
    Load device.

    Only needs to reply with the load it represents on the system.

    It can only have one input neighbor.
    '''

    def __init__(self, guid: int, neighbors_in: list, neighbors_out: list, **kwargs):
        assert all(val is not None for val in [guid, neighbors_in])
        assert all(isinstance(val, int) for val in neighbors_in)
        assert len(neighbors_in) >= 1
        assert 'load' in kwargs.keys()
        assert isinstance(kwargs['load'], float)
        super().__init__(guid, neighbors_in=neighbors_in[:1], neighbors_out=[], **kwargs)
        self._load = kwargs['load']
        self._vin = None
        self._amp = None
    
    def __str__(self) -> str:
        if all(x is not None for x in [self._vin, self._load, self._amp]):
            return f'Vin:  {self._vin:6.3f} V\r\nI:    {self._amp:6.3f}\r\nR:    {self._load:6.3f} Ohm\r\n'
        return 'Awaiting data from configured neighbors ...\r\n'

    @property
    def load(self) -> float:
        return self._load
    
    @load.setter
    def load(self, value: float):
        self._load = value if value >= 0 else self._load
        # A zero-valued load represents a failure

    def handle_specific(self, message: simproto.NEFICSMSG):
        if message.SenderID in self._n_in_addr.keys():
            addr = self._n_in_addr[message.SenderID]
            if addr is not None:
                if message.MessageID == simproto.MESSAGE_ID['MSG_GREQ']:
                    pkt = simproto.NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID = simproto.MESSAGE_ID['MSG_TREQ'],
                        FloatArg0 = self.load
                    )
                elif message.MessageID == simproto.MESSAGE_ID['MSG_VOLT']:
                    pkt = None
                    self._vin = message.FloatArg0
                else:
                    self._log(f'Received a NEFICS message not supported by simplepowergrid.Load from {addr}: {repr(message)}')
                    pkt = simproto.NEFICSMSG(
                        SenderID=self.guid,
                        ReceiverID=message.SenderID,
                        MessageID=simproto.MESSAGE_ID['MSG_UKWN']
                    )
                if pkt is not None:
                    self._sock.sendto(pkt.build(), addr)
    
    def simulate(self):
        if all(x is not None for x in self._n_in_addr.values()):
            # Request input voltage to neighbor
            dstid = list(self._n_in_addr.keys())[0]
            addr = self._n_in_addr[dstid]
            pkt = simproto.NEFICSMSG(
                SenderID=self.guid,
                ReceiverID=dstid,
                MessageID=simproto.MESSAGE_ID['MSG_GETV']
            )
            self._sock.sendto(pkt.build(), addr)
            sleep(0.5)
        if all(x is not None for x in [self._load, self._vin]):
            if self.load == float('inf'):
                # Failure condition - Open circuit
                self._amp = 0
            else:
                try:
                    self._amp = self._vin / self.load
                except ZeroDivisionError:
                    # Short-circuit on load
                    self._log(f'Load (GUID:{self.guid}) is in short circuit condition', devicebase.LOG_PRIO['CRITICAL'])
                    self._amp = float('inf')

    def poll_values_IEC104(self) -> list:
        iframes = []
        if all(x is not None for x in [self._vin, self._amp]):
            # Input voltage
            ioa = IOA36(IOA=BASE_IOA, Value=self._vin, QDS=0, CP56Time=devicebase.cp56time())
            pkt = APDU()
            pkt /= APCI(ApduLen=25, Type=0x00, Tx=self.tx, Rx=self.rx)
            pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
            self.tx += 1
            iframes.append(pkt)
            # Measured current
            ioa = IOA36(IOA=BASE_IOA + 1, Value=self._amp, QDS=0, CP56Time=devicebase.cp56time())
            pkt = APDU()
            pkt /= APCI(ApduLen=25, Type=0x00, Tx=self.tx, Rx=self.rx)
            pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
            self.tx += 1
            iframes.append(pkt)
        return iframes

    def handle_IEC104_IFrame(self, packet: APDU) -> APDU:
        # A load device shouldn't receive any I-Frames
        assert packet.haslayer('APCI')
        assert packet.haslayer('ASDU')
        apci:APCI = packet['APCI']
        self.tx = apci.Tx + 1
        self.rx = apci.Rx + 1
        response:APDU = packet
        response['APCI'].Rx = self.rx
        response['APCI'].Tx = self.tx
        response['ASDU'].CauseTx = 45 # Unknown CoT
        return response

#!/usr/bin/env python3

from IEC104_Raw.dissector import APDU
from iec104 import IEC104, get_command
import socket
from threading import Thread
from time import sleep

RTU_TYPES = [
    'SOURCE',
    'TRANSMISSION',
    'LOAD'
]

RTU_SOURCE = 0
RTU_TRANSMISSION = 1
RTU_LOAD = 2

BREAKERS = {
    101: 0x1, # 001
    102: 0x2, # 010
    103: 0x4  # 100
}

IEC104_PORT = 2404
BUFFER_SIZE = 512

class RTU:

    def __init__(self, **kwargs):
        fields = ['guid', 'type']
        if any(k not in kwargs.keys() or not isinstance(kwargs[k], int) for k in fields):
            raise AttributeError()
        self.__guid = kwargs['guid']
        self.__type = kwargs['type']
        self.__terminate = False
        self.__tx = 0
        self.__rx = 0
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind(('0.0.0.0', IEC104_PORT))

    @property
    def guid(self) -> int:
        return self.__guid
    @guid.setter
    def guid(self, new_guid: int):
        self.__guid = new_guid

    @property
    def rtutype(self) -> int:
        return self.__type
    @rtutype.setter
    def rtutype(self, new_type: int):
        self.__type = new_type

    @property
    def sock(self) -> socket.socket:
        return self.__socket
    @sock.setter
    def sock(self, value: socket.socket):
        self.__socket = value
    
    @property
    def terminate(self) -> bool:
        return self.__terminate
    @terminate.setter
    def terminate(self, value: bool):
        self.__terminate = value

    @property
    def tx(self) -> int:
        return self.__tx
    @tx.setter
    def tx(self, value: int):
        self.__tx = value
    
    @property
    def rx(self) -> int:
        return self.__rx
    @rx.setter
    def rx(self, value: int):
        self.__rx = value

    # def get_pack(self, dato):


    def loop(self):
        'Override this'
    
    def __str__(self):
        return 'RTU\r\n------------------\r\nID: {0:11d}\r\nType: {1:12s}'.format(self.__guid, RTU_TYPES[self.__type])
    
    def __repr__(self):
        return 'RTU({0:d}, {1:d})'.format(self.__guid, self.__type)

class Source(RTU):

    def __init__(self, **kwargs):
        super(Source, self).__init__(**kwargs)
        if 'voltage' not in kwargs.keys() or not isinstance(kwargs['voltage'], float):
            raise AttributeError()
        self.__voltage = kwargs['voltage']
        self.__confok = True

    @property
    def voltage(self) -> float:
        return self.__voltage
    @voltage.setter
    def voltage(self, value: float):
        self.__voltage = value
        self.__ioaV = IEC104(36, 1001)
    
    def __str__(self):
        return 'Source RTU\r\n----------------\r\nID: {0:11d}\r\nVout: {1:6.2f}'.format(self.guid, self.__voltage)
    
    def __repr__(self):
        return 'Source RTU ({0:d}, {1:.2f})'.format(self.guid, self.__voltage)

    
    def subloop(self, wsock: socket.socket):
        while not self.terminate:
            if all(x is not None for x in [self.tx, self.rx]):
                self.tx += 1
                if self.tx == 65536:
                    self.tx = 0
                data = self.__ioaV.get_apdu(self.__voltage, self.tx, self.rx)
                wsock.send(data)
            sleep(1)
        wsock.close()
    
    def loop(self):
        self.sock.settimeout(0.25)
        self.sock.listen(1)
        threads = []
        while not self.terminate:
            try:
                wsock, addr = self.sock.accept()
                if not self.__confok or len(threads) == 0:
                    wsock.settimeout(0.25)
                    t = Thread(target=self.subloop, kwargs={'wsock': wsock})
                    threads.append(t)
                    t.start()
                else:
                    wsock.close()
            except socket.timeout:
                pass
        for t in threads:
            t.join()
        self.sock.close()

class Transmission(RTU):

    def __init__(self, **kwargs):
        super(Transmission, self).__init__(**kwargs)
        if any(k not in kwargs.keys() for k in ['state', 'loads', 'left', 'right', 'confok']):
            raise AttributeError()
        if any(not isinstance(kwargs[k], int) for k in ['state', 'left', 'right']) or not isinstance(kwargs['loads'], list):
            raise AttributeError()
        if any(not isinstance(k, float) for k in kwargs['loads']):
            raise AttributeError()
        if not isinstance(kwargs['confok'], bool):
            raise AttributeError()
        self.__state = kwargs['state']
        self.__loads = kwargs['loads']
        self.__left = kwargs['left']
        self.__right = kwargs['right']
        self.__confok = kwargs['confok']
        self.__load = None
        self.__vin = None
        self.__vout = None
        self.__amp = None
        self.__rload = None
        self.__ioaV = IEC104(36, 1001)
        self.__ioaI = IEC104(36, 1002)
        self.__ioaBR = {}
        for i in BREAKERS.keys():
            self.__ioaBR[i] = [ IEC104(3, i), IEC104(50, i) ]

    @property
    def state(self) -> float:
        return self.__state
    @state.setter
    def state(self, value: float):
        self.__state = value

    @property
    def left(self) -> float:
        return self.__left
    @left.setter
    def left(self, value: float):
        self.__left = value

    @property
    def right(self) -> float:
        return self.__right
    @right.setter
    def right(self, value: float):
        self.__right = value

    @property
    def load(self) -> float:
        return self.__load
    @load.setter
    def load(self, value: float):
        self.__load = value

    @property
    def vin(self) -> float:
        return self.__vin
    @vin.setter
    def vin(self, value: float):
        self.__vin = value

    @property
    def vout(self) -> float:
        return self.__vout
    @vout.setter
    def vout(self, value: float):
        self.__vout = value
    
    @property
    def rload(self) -> float:
        return self.__rload
    @rload.setter
    def rload(self, value: float):
        self.__rload = value
    
    @property
    def amp(self) -> float:
        return self.__amp
    @amp.setter
    def amp(self, value: float):
        self.__amp = value

    def calculate_load(self):
        self.__load = None
        if self.__state == 0:
            self.__load = float('inf')
            return
        for i in range(len(self.__loads)):
            if (self.__state & (2 ** i)) > 0:
                if self.__loads[i] == 0:
                    self.__load = 0 # Failure
                    return
                self.__load = self.__loads[i] if self.__load is None else (self.__load * self.__loads[i]) / (self.__load + self.__loads[i])

    def receive_command(self, sock: socket.socket):
        while not self.terminate:
            try:
                data = APDU(sock.recv(BUFFER_SIZE))
                data = get_command(data)
                self.tx = data['rx'] + 1
                self.rx = data['tx'] + 1
                if self.tx == 65536:
                    self.tx = 0
                if self.rx == 65536:
                    self.rx = 0
                sock.send(self.__ioaBR[data['ioa']][1].get_apdu(data['value'], data['rx'] + 1, data['tx'] + 1, 7))
                if bool(data['value']):
                    self.__state = self.__state | BREAKERS[data['ioa']] # STATE OR IOA
                else: 
                    self.__state = self.__state & (BREAKERS[data['ioa']] ^ 0x7) # STATE AND (IOA XOR 111)
            except socket.timeout:
                pass

    def subloop(self, wsock: socket.socket):
        cmd = Thread(target=self.receive_command, kwargs={'sock': wsock})
        cmd.start()
        while not self.terminate:
            if all(x is not None for x in [self.tx, self.rx]):
                self.tx += 1
                if self.tx == 65536:
                    self.tx = 0
                data = self.__ioaV.get_apdu(self.__vin - self.__vout, self.tx, self.rx)
                wsock.send(data)
                self.tx += 1
                if self.tx == 65536:
                    self.tx = 0
                data = self.__ioaI.get_apdu((self.__vin - self.__vout)/self.__load, self.tx, self.rx)
                wsock.send(data)
                for i in self.__ioaBR.keys():
                    if self.tx == 65536:
                        self.tx = 0
                    data = self.__ioaBR[i][0].get_apdu((self.__state & BREAKERS[i]) / BREAKERS[i], self.tx, self.rx)
                    wsock.send(data)
            sleep(1)
        cmd.join()
        wsock.close()
    
    def loop(self):
        self.sock.settimeout(0.25)
        self.sock.listen(1)
        threads = []
        while not self.terminate:
            try:
                wsock, addr = self.sock.accept()
                if not self.__confok or len(threads) == 0:
                    wsock.settimeout(0.25)
                    t = Thread(target=self.subloop, kwargs={'wsock': wsock})
                    threads.append(t)
                    t.start()
                else:
                    wsock.close()
            except socket.timeout:
                pass
        for t in threads:
            t.join()
        self.sock.close()

class Load(RTU):

    def __init__(self, **kwargs):
        super(Load, self).__init__(**kwargs)
        if any(k not in kwargs.keys() for k in ['load', 'left']):
            raise AttributeError()
        if not isinstance(kwargs['load'], float) or not isinstance(kwargs['left'], int):
            raise AttributeError()
        self.__load = kwargs['load']
        self.__left = kwargs['left']
        self.__confok = True
        self.__vin = None
        self.__amp = None
        self.__ioaV = IEC104(36, 1001)
        self.__ioaI = IEC104(36, 1002)

    @property
    def load(self) -> float:
        return self.__load
    @load.setter
    def load(self, new_load: float):
        self.__load = new_load
    
    @property
    def left(self) -> int:
        return self.__left
    @left.setter
    def left(self, value: int):
        self.__left = value

    @property
    def vin(self) -> float:
        return self.__vin
    @vin.setter
    def vin(self, value: float):
        self.__vin = value

    def __str__(self):
        return 'Load RTU\r\n-------------------\r\nID: {0:14d}\r\nLoad: {1:9.2f}'.format(self.guid, self.__load)
    
    def __repr__(self):
        return 'Load RTU ({0:d}, {1:.2f})'.format(self.guid, self.__load)

    def subloop(self, wsock: socket.socket):
        while not self.terminate:
            if all(x is not None for x in [self.tx, self.rx]):
                self.tx += 1
                if self.tx == 65536:
                    self.tx = 0
                data = self.__ioaV.get_apdu(self.__vin, self.tx, self.rx)
                wsock.send(data)
                self.tx += 1
                if self.tx == 65536:
                    self.tx = 0
                data = self.__ioaI.get_apdu(self.__vin/self.load, self.tx, self.rx)
                wsock.send(data)
            sleep(1)
        wsock.close()
    
    def loop(self):
        self.sock.settimeout(0.25)
        self.sock.listen(1)
        threads = []
        while not self.terminate:
            try:
                wsock, addr = self.sock.accept()
                if not self.__confok or len(threads) == 0:
                    wsock.settimeout(0.25)
                    t = Thread(target=self.subloop, kwargs={'wsock': wsock})
                    threads.append(t)
                    t.start()
                else:
                    wsock.close()
            except socket.timeout:
                pass
        for t in threads:
            t.join()
        self.sock.close()
    
    


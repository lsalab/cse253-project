#!/usr/bin/env python3

import sys
import socket
from struct import pack, unpack
from threading import Thread
from rtu import RTU_SOURCE, RTU_TRANSMISSION, RTU_LOAD, RTU_TYPES

SIM_PORT = 20202
BUFFER_SIZE = 512
DATA_FMT = '<IIIIIff' # Sender-ID Receiver-ID Message-ID IARG-0 IARG-1 FARG-0 FARG-1

# Message ID
MSG_WERE = 0
MSG_ISAT = 1
MSG_GETV = 2
MSG_VOLT = 3
MSG_GREQ = 4
MSG_TREQ = 5
MSG_NONE = 98
MSG_UKWN = 99

class ClassTypeMismatch(Exception):
    pass

class SimulationHandler(Thread):

    def __init__(self, rtu):
        super(SimulationHandler, self).__init__()
        if rtu is None or rtu.__class__.__name__ not in ['Load', 'Transmission', 'Source', 'RTU']:
            raise AttributeError()
        self.__rtu = rtu
        self.__terminate = False
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)      # Use UDP
        if sys.platform not in ['win32']:
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)                   # Enable port reusage
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)                       # Enable broadcast
        self.__sock.bind(('', SIM_PORT))
        self.__sock.settimeout(0.333)
    
    @property
    def terminate(self) -> bool:
        return self.__terminate
    
    @terminate.setter
    def terminate(self, value: bool):
        self.__terminate = value
    
    def run_source(self):
        while not self.__terminate:
            try:
                data, addr = self.__sock.recvfrom(BUFFER_SIZE)
                data = unpack(DATA_FMT, data) 
                if data[1] == self.__rtu.guid:
                    if data[2] == MSG_WERE:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_ISAT, 0, 0, 0.0, 0.0)
                    elif data[2] == MSG_GETV:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_VOLT, 0, 0, self.__rtu.voltage, 0.0)
                    else:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_UKWN, 0, 0, 0.0, 0.0)
                    self.__sock.sendto(data, addr)
            except socket.timeout:
                pass
    
    def run_load(self):
        while not self.__terminate:
            try:
                data, addr = self.__sock.recvfrom(BUFFER_SIZE)
                data = unpack(DATA_FMT, data)
                if data[1] == self.__rtu.guid:
                    if data[2] == MSG_WERE:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_ISAT, 0, 0, 0.0, 0.0)
                    elif data[2] == MSG_GREQ:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_TREQ, 0, 0, self.__rtu.load, 0.0)
                    else:
                        data = pack(DATA_FMT, self.__rtu.guid, data[0], MSG_UKWN, 0, 0, 0.0, 0.0)
            except socket.timeout:
                pass

    def run(self):
        if self.__rtu.rtutype == RTU_SOURCE and isinstance(self.__rtu, Source):
            self.run_source()
        else:
            raise ClassTypeMismatch()

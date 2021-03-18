#!/usr/bin/env python3

from nefics.IEC104.const import DPI_ENUM
import sys
from netaddr import valid_ipv4
from types import FrameType
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket, timeout

# NEFICS imports
from nefics.IEC104.dissector import APDU, APCI

IEC104_PORT = 2404
IEC104_T1 = 15
BUFFER_SIZE = 65536

IOA_ADDR_MAP = {
    1001: 'Voltage',
    1002: 'Current'
}

class IEC104Poller(object):

    def __init__(self, address:str):
        super().__init__()
        assert valid_ipv4(address)
        self._terminate = False
        self._sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        self._sock.settimeout(IEC104_T1)
        try:
            self._sock.connect((address, IEC104_PORT))
        except timeout:
            print('[!] Socket connection timeout')
            sys.exit()
        print('[+] Connection established')
    
    def terminate(self, signum:int, stack_frame:FrameType):
        self._terminate = True

    def loop(self):
        try:
            print('[*] Sending STARTDT U-Frame ... ', end='')
            apdu = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x01)
            self._sock.send(apdu.build())
            data = self._sock.recv(BUFFER_SIZE)
            apdu = APDU(data)
            if apdu['APCI'].Type != 0x03 or apdu['APCI'].UType != 0x02:
                print(f'ERROR\r\n[!] Unexpected Frame: {repr(apdu)}')
            print('Confirmed')
            while not self._terminate:
                data = self._sock.recv(BUFFER_SIZE)
                apdu = APDU(data)
                if apdu['ASDU'].TypeId == 36:
                    print(f"[+] Received type 36 ASDU :: [{IOA_ADDR_MAP[apdu['IOA36'].IOA]}] Value: {apdu['IOA36'].Value}")
                elif apdu['ASDU'].TypeId == 3:
                    print(f"[+] Received type 3 ASDU :: [Breaker status] Breaker ID: {apdu['IOA3'].IOA} Status: {DPI_ENUM[apdu['DIQ'].DPI]} (0x{apdu['DIQ'].DPI:02x})")
                else:
                    print(f'[!] Received an unknown ASDU :: {repr(apdu)}')
                print('[*] Sending TESTFR U-Frame ... ', end='')
                apdu = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x10)
                self._sock.send(apdu.build())
                data = self._sock.recv(BUFFER_SIZE)
                apdu = APDU(data)
                if apdu['APCI'].Type != 0x03 or apdu['APCI'].UType != 0x20:
                    print(f'FATAL\r\n[!] Unexpected frame: {repr(apdu)}')
                    self._sock.close()
                    sys.exit()
                print('Confirmed')
            print('[*] Sending STOPDT U-Frame ... ')
            apdu = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x04)
            self._sock.send(apdu.build())
            data = self._sock.recv(BUFFER_SIZE)
            apdu = APDU(data)
            while apdu['APCI'].Type != 0x03 or apdu['APCI'].UType != 0x08:
                print('[!] Received pending Frame:', repr(apdu))
                data = self._sock.recv(BUFFER_SIZE)
                apdu = APDU(data)
            print('[*] STOPDT confirmed')
            print('[*] Closing connection ...')
            self._sock.close()
        except timeout:
            print('Socket timeout')
            sys.exit()


if __name__ == '__main__':
    import argparse
    import signal
    aparser = argparse.ArgumentParser(description='IEC 60870-4-104 device poller')
    aparser.add_argument('address', action='store', type=str, metavar='IPv4_ADDRESS')
    args = aparser.parse_args()
    try:
        poller = IEC104Poller(args.address)
    except AssertionError:
        print(f'Invalid IPv4 address: "{args.address}"')
        sys.exit()
    signal.signal(signal.SIGINT, poller.terminate)
    signal.signal(signal.SIGTERM, poller.terminate)
    poller.loop()

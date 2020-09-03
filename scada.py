#!/usr/bin/env python3

import re
import socket
from prompt_toolkit.shortcuts import run_application as runprompt
from PyInquirer.prompts.list import question as listq
from threading import Thread
from cmd import Cmd
from time import sleep
from helper104 import *
from IEC104.dissector import APDU, APCI

BUFFER_SIZE = 512
IEC104_PORT = 2404
IPv4_REGEX = re.compile(r'^(?:(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)\.){3}(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)(?:\/\d\d)?$', re.DOTALL | re.MULTILINE)

IOAS = {
    1001: ['Voltage', 'V'],
    1002: ['Current', 'A'],
    101: ['Breaker', 'Open/Close'],
    102: ['Breaker', 'Open/Close'],
    103: ['Breaker', 'Open/Close'],
}

class SCADACLI(Cmd):

    def __init__(self):
        super(SCADACLI, self).__init__()
        self.prompt = 'SCADA>'
        self.__rtu_comms = {}
        self.__threads = {}
        self.__keepalive = {}
        self.__keepalive_kill = {}
        self.__killsignals = {}
        self.__rtu_data = {}
        self.__rtu_u_state = {}
        self.__rtu_i_state = {}
        self.__rtu_asdu = {}
        self.__done  = False
    
    def emptyline(self):
        pass

    def __keepalive_handler(self, s: socket.socket, k:str):
        while not self.__done and not self.__keepalive_kill[k]:
            sleep(10) # Send a keepalive every 10 seconds
            self.__rtu_u_state[k] = 0x20 # Expect a TESTFR con
            pkt = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x10) # 'TESTFR act' as a keepalive
            self.__rtu_comms[k].send(pkt.build())
            while self.__rtu_u_state[k] is not None and self.__rtu_u_state[k] > 0:
                sleep(0.33)

    def __handle_rtu(self, s: socket.socket, k: str):
        if k not in self.__rtu_data.keys():
            self.__rtu_data[k] = {'ioas': {}}
        while not self.__done and not self.__killsignals[k]:
            try:
                data = s.recv(BUFFER_SIZE)
                data = APDU(data)
                if data['APCI'].Type == 0x03: # U-frame
                    if data['APCI'].UType in [1, 4, 16]: # All the 'act' variants => Shouldn't happen. Do nothing
                        pass
                    elif data['APCI'].UType == self.__rtu_u_state[k]: # Correct expected U-frame response
                        self.__rtu_u_state[k] = 0
                    else: # Unexpected U-frame response => Shouldn't happen. Alert user.
                        print(f'**** WARNING: Received an unexpected U-frame from {str(self.__rtu_comms[k].getpeername()):s} ****')
                        self.__rtu_u_state[k] = None
                elif data['APCI'].Type == 0x01: # S-frame => Shouldn't happen. Alert user.
                    print(f'**** WARNING: Received an S-frame from {str(self.__rtu_comms[k].getpeername()):s} ****')
                elif data['APCI'].Type == 0x00: # I-frame
                    asdu = data['ASDU']
                    data = extract_104_value(data)
                    self.__rtu_data[k]['tx'] = data['rx']
                    self.__rtu_data[k]['rx'] = data['tx']
                    if asdu.TypeId in [3, 36]: # Measurement value
                        value = data['value']
                        if isinstance(value, str):
                            if value == 'determined state OFF':
                                value = 0
                            else:
                                value = 1
                        self.__rtu_data[k]['ioas'][data['ioa']] = value
                    elif asdu.TypeId == 45: # Single command
                        if self.__rtu_i_state[k] is not None and self.__rtu_i_state[k] == ((asdu['IOA45'].CauseTx << 8) | asdu['IOA45'].SCO.SE): # Expected single command response
                            self.__rtu_i_state[k] = 0x0000
                        else: # Unexpected single command response => Alert user.
                            self.__rtu_i_state[k] = None
                            print(f'**** WARNING: Received an unexpected I-frame from {str(self.__rtu_comms[k].getpeername()):s} ****')
                    else: # Received an I-frame that has not been implemented => Alert user.
                        print(f'**** WARNING: Received an unknown I-frame from {str(self.__rtu_comms[k].getpeername()):s} ****')
                else: # Received a malformed packet => Alert user.
                    print(f'**** WARNING: Received a malformed packet from {str(self.__rtu_comms[k].getpeername()):s} ****')
            except (socket.timeout, KeyError, IndexError):
                self.__rtu_i_state[k] = None
                self.__rtu_u_state[k] = None
            except ConnectionResetError:
                self.__rtu_i_state[k] = None
                self.__rtu_u_state[k] = None

    def do_connect(self, arg: str):
        'Connect to a new RTU'
        try:
            arg = arg.split(';')
            self.__rtu_asdu[arg[0]] = arg[1]
            arg = arg[0]
            assert IPv4_REGEX.match(arg) is not None
            if '/' in arg:
                prefix = int(arg.split('/')[1])
                assert prefix > 0 and prefix <= 32
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            s.settimeout(2)
            s.connect((arg, IEC104_PORT))
            self.__rtu_comms[arg] = s
            self.__killsignals[arg] = False
            self.__rtu_u_state[arg] = 0x02 # Expect a STARTDT con U-frame
            self.__rtu_i_state[arg] = None # Don't expect any I-frames
            t = Thread(target=self.__handle_rtu, kwargs={'s': s, 'k': arg}) # Create a receiving thread for this RTU.
            t.start()
            self.__threads[arg] = t
            pkt = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x01) # STARTDT act
            s.send(pkt.build())
            while self.__rtu_u_state[arg] is not None and self.__rtu_u_state[arg] > 0:
                print(f'\rInitiating connection with peer {arg:s} ... ', end='')
                sleep(0.33)
            print('')
            if self.__rtu_u_state[arg] is None:
                print(f'Unable to connect to {arg:s}')
                self.__killsignals[arg] = True
                t = self.__threads.pop(arg)
                t.join()
                s.close()
                self.__rtu_asdu.pop(arg)
                self.__rtu_comms.pop(arg)
                self.__killsignals.pop(arg)
                self.__rtu_i_state.pop(arg)
                self.__rtu_u_state.pop(arg)
                if arg in self.__rtu_data.keys():
                    self.__rtu_data.pop(arg)
            else:
                self.__keepalive_kill[arg] = False
                t = Thread(target=self.__keepalive_handler, kwargs={'s': s, 'k': arg}) # Create a keepalive thread for this RTU.
                t.start()
                self.__keepalive[arg] = t
        except AssertionError:
            print('Invalid IPv4 address: %s' % arg)
        except socket.timeout:
            print('Unable to connect to %s' % arg)
        return False
    
    def do_disconnect(self, arg:str):
        'Disconnect from an RTU'
        if len(self.__rtu_comms) > 0:
            rtuaddr = runprompt(listq(message='Disconnect from which RTU?', choices=self.__rtu_comms.keys()))
            self.__keepalive_kill[rtuaddr] = True # Stop keepalive
            t = self.__keepalive[rtuaddr]
            t.join()
            self.__rtu_u_state[rtuaddr] = 0x08 # Expect STOPDT con
            pkt = APDU()/APCI(ApduLen=4, Type=0x03, UType=0x04) # STOPDT act
            self.__rtu_comms[rtuaddr].send(pkt.build())
            while self.__rtu_u_state[rtuaddr] is not None and self.__rtu_u_state > 0:
                print(f'\rTerminating connection with {rtuaddr:s} ... ', end='')
                sleep(0.33)
            print('')
            self.__killsignals[rtuaddr] = True
            t = self.__threads.pop(rtuaddr)
            t.join()
            s = self.__rtu_comms.pop(rtuaddr)
            d = self.__rtu_data.pop(rtuaddr)
            k = self.__killsignals.pop(rtuaddr)
            self.__rtu_asdu.pop(rtuaddr)
            s.close()
        else:
            print('Not connected to any RTUs')

    def do_send(self, arg):
        'Send a command to an RTU'
        if len(self.__rtu_comms) > 0:
            rtuaddr = runprompt(listq(message='Send a command to which RTU?', choices=self.__rtu_comms.keys()))
            breakers = []
            for i in self.__rtu_data[rtuaddr]['ioas'].keys():
                if IOAS[i][0] == 'Breaker':
                    breakers.append(str(i))
            if len(breakers) > 0:
                ioa = int(runprompt(listq(message='Send command to which IOA?', choices=breakers)))
                status = int(self.__rtu_data[rtuaddr]['ioas'][ioa])
                if status == 0:
                    print('The last known state is CLOSED')
                    ans = runprompt(listq(message='Would you like to OPEN this IOA?', choices=['Yes', 'No']))
                else:
                    print('The last known state is OPEN')
                    ans = runprompt(listq(message='Would you like to CLOSE this IOA?', choices=['Yes', 'No']))
                if ans == 'Yes':
                    status = status ^ 0x1
                    self.__rtu_data[rtuaddr]['tx'] += 1
                    self.__rtu_u_state[rtuaddr] = (0x07 << 8) | 0x80 | status
                    pkt = build_104_asdu_packet(45, self.__rtu_asdu[rtuaddr], ioa, self.__rtu_data[rtuaddr]['tx'], self.__rtu_data[rtuaddr]['rx'], 6, SE=0x80, QU=0x01, SCS=status)
                    self.__rtu_comms[rtuaddr].send(pkt)
                    while self.__rtu_u_state[rtuaddr] is not None and self.__rtu_u_state[rtuaddr] > 0:
                        print(f'\rSending single command (SELECT) to {rtuaddr:s} ... ')
                        sleep(0.25)
                    print('')
                    if self.__rtu_u_state[rtuaddr] is None:
                        print(f'Error sending command to {rtuaddr:s}')
                    else:
                        self.__rtu_u_state[rtuaddr] = (0x07 << 8) | status
                        pkt = build_104_asdu_packet(45, self.__rtu_asdu[rtuaddr], ioa, self.__rtu_data[rtuaddr]['tx'], self.__rtu_data[rtuaddr]['rx'], 6, SE=0x00, QU=0x01, SCS=status)
                        self.__rtu_comms[rtuaddr].send(pkt)
                        while self.__rtu_u_state[rtuaddr] is not None and self.__rtu_u_state[rtuaddr] > 0:
                            print(f'\rSending single command (EXECUTE) to {rtuaddr:s} ... ')
                            sleep(0.25)
                        print('')
            else:
                print('This RTU cannot receive any commands')
        else:
            print('''Not connected to any RTUs''')
        return False
    
    def do_status(self, arg):
        'Get the status of an RTU'
        if len(self.__rtu_comms) > 0:
            if arg and arg not in self.__rtu_data.keys():
                print('RTU %s not found' % arg)
                return False
            elif arg:
                addr = arg
            else:
                addr = runprompt(listq(message='Get the status of which RTU?', choices=self.__rtu_comms.keys()))
            data = self.__rtu_data[addr]['ioas']
            print('\r\nCurrent status of RTU %s:' % addr)
            print('='*40)
            for k, v in data.items():
                print('IOA %d:' % k)
                print('-'*15)
                print('Type: %s' % IOAS[k][0])
                value = v
                if IOAS[k][0] is not 'Breaker':
                    print('Value: {0:5.12f} {1:s}'.format(value, IOAS[k][1]))
                else:
                    value = 'OPEN' if value == 0 else 'CLOSED'
                    print('Value: %s' % value)
            print('='*40 + '\r\n')
        else:
            print('''Not connected to any RTUs''')
        return False

    def do_exit(self, arg):
        'Close RTU connections and exit'
        self.__done = True
        for k, t in self.__threads.items():
            t.join()
        for k, t in self.__keepalive_handler.items():
            t.join()
        for k, s in self.__rtu_comms.items():
            s.close()
        return True

if __name__ == '__main__':
    SCADACLI().cmdloop()

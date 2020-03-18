#!/usr/bin/env python3

import re
import socket
from prompt_toolkit.shortcuts import run_application as runprompt
from PyInquirer.prompts.list import question as listq
from threading import Thread
from cmd import Cmd
from iec104 import IEC104, get_command
from IEC104_Raw.dissector import APDU

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
        self.__rtu_data = {}
        self.__done  = False
    
    def emptyline(self):
        pass

    def handle_rtu(self, s: socket.socket, k: str):
        if k not in self.__rtu_data.keys():
            self.__rtu_data[k] = {'ioas': {}}
        while not self.__done:
            try:
                data = s.recv(BUFFER_SIZE)
                data = get_command(APDU(data))
                self.__rtu_data[k]['tx'] = data['rx']
                self.__rtu_data[k]['rx'] = data['tx']
                value = data['value']
                if isinstance(value, str):
                    if value == 'determined state OFF':
                        value = 1
                    else:
                        value = 0
                self.__rtu_data[k]['ioas'][data['ioa']] = value
            except socket.timeout:
                pass

    def do_connect(self, arg: str):
        'Connect to a new RTU'
        try:
            assert IPv4_REGEX.match(arg) is not None
            if '/' in arg:
                prefix = int(arg.split('/')[1])
                assert prefix > 0 and prefix <= 32
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            s.settimeout(2)
            s.connect((arg, IEC104_PORT))
            self.__rtu_comms[arg] = s
            t = Thread(target=self.handle_rtu, kwargs={'s': s, 'k': arg})
            t.start()
            self.__threads[arg] = t
        except AssertionError:
            print('Invalid IPv4 address: %s' % arg)
        except socket.timeout:
            print('Unable to connect to %s' % arg)
        return False

    def do_send(self, arg):
        'Send a command to an RTU'
        if len(self.__rtu_comms) > 0:
            rtuaddr = runprompt(listq(message='Send a command to which RTU?', choices=self.__rtu_comms.keys()))
            breakers = []
            for i in self.__rtu_data[rtuaddr]['ioas'].keys():
                if IOAS[i][0] == 'Breaker':
                    breakers.append(str(i))
            ioa = int(runprompt(listq(message='Send command to which IOA?', choices=breakers)))
            status = int(self.__rtu_data[rtuaddr]['ioas'][ioa])
            if status == 0:
                print('The last known state is OPEN')
                ans = runprompt(listq(message='Would you like to CLOSE this IOA?', choices=['Yes', 'No']))
            else:
                print('The last known state is CLOSE')
                ans = runprompt(listq(message='Would you like to OPEN this IOA?', choices=['Yes', 'No']))
            if ans == 'Yes':
                status = status ^ 0x1
                self.__rtu_data[rtuaddr]['tx'] += 1
                data = IEC104(50, ioa).get_apdu(status, self.__rtu_data[rtuaddr]['tx'], self.__rtu_data[rtuaddr]['rx'], 1)
                self.__rtu_comms[rtuaddr].send(data)
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
            print('Current status of RTU %s:' % addr)
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
        else:
            print('''Not connected to any RTUs''')
        return False

    def do_exit(self, arg):
        'Close RTU connections and exit'
        self.__done = True
        for k, t in self.__threads.items():
            t.join()
        for k, s in self.__rtu_comms.items():
            s.close()
        return True

if __name__ == '__main__':
    SCADACLI().cmdloop()

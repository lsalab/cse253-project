#!/usr/bin/env python3

import re
import socket
from prompt_toolkit.shortcuts import run_application as runprompt
from PyInquirer.prompts.list import question as listq
from threading import Thread
from cmd import Cmd

BUFFER_SIZE = 512
IEC104_PORT = 2404
IPv4_REGEX = re.compile(r'^(?:(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)\.){3}(?:2(?:5[0-5]|[0-4]\d)|1\d\d|[1-9]?\d)(?:/\d\d)$', re.DOTALL | re.MULTILINE)

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
        while not self.__done:
            try:
                data = s.recv(BUFFER_SIZE)
                # TODO Handle IEC104 packet
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

    def do_send(self, arg):
        if len(self.__rtu_comms) > 0:
            rtuaddr = runprompt(listq(message='Send a command to which RTU?', choices=self.__rtu_comms.keys()))
        else:
            print('''Not connected to any RTUs''')

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

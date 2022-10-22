#!/usr/bin/env python3

import os
import sys
import signal
from time import sleep
from threading import Thread

from nefics.modules.devicebase import IEDBase

def launcher_main():
    from importlib import import_module
    import io
    import argparse
    import json
    # Acquire configuration values for the device
    aparser = argparse.ArgumentParser(description='NEFICS Simulated device launcher')
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
        required_values = ['module', 'handler', 'device', 'guid', 'in', 'out', 'parameters']
        assert all(x in config.keys() for x in required_values)
    except AssertionError:
        sys.stderr.write(f'Corrupt configuration detected. Missing values: {", ".join([x for x in required_values if x not in config.keys()])}\r\n')
        sys.stderr.flush()
        sys.exit()
    # Assert whether the provided values are correctly typed
    try:
        assert all(isinstance(x, str) for x in [config['module'], config['handler'], config['device']])
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
        device_class = getattr(device_module, config['device'])
    except AttributeError:
        sys.stderr.write(f'Could not find class "{config["device"]}" in module "nefics.modules.{config["module"]}"\r\n')
        sys.stderr.flush()
        sys.exit()
    # Instantiate the device and assert whether it is compatible (devicebase.IEDBase)
    device = device_class(config['guid'], config['in'], config['out'], **config['parameters'])
    try:
        assert isinstance(device, IEDBase)
    except AssertionError:
        sys.stderr.write(f'Instantiated device ({device_class.__name__}) is not supported by NEFICS\r\n')
        sys.stderr.flush()
        sys.exit()
    # Try to get the configured handler from the specified module
    try:
        handler_class = getattr(device_module, config['handler'])
    except AttributeError:
        sys.stderr.write(f'Could not find class "{config["handler"]}" in module "nefics.modules.{config["module"]}"\r\n')
        sys.stderr.flush()
        sys.exit()
    handler = handler_class(device)
    try:
        assert isinstance(handler, Thread)
    except AssertionError:
        sys.stderr.write(f'Instantiated handler ({handler.__name__}) is not supported by NEFICS\r\n')
        sys.stderr.flush()
        sys.exit()
    signal.signal(signal.SIGINT, handler.set_terminate)
    signal.signal(signal.SIGTERM, handler.set_terminate)

    def clearscreen():
        if os.name == 'nt':
            _ = os.system('cls')
        else:
            _ = os.system('clear')
    
    handler.start()
    while not handler.terminate:
        clearscreen()
        handler.status()
        sleep(10)
    handler.join()
    
if __name__ == '__main__':
    launcher_main()
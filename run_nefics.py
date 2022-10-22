#!/usr/bin/env python3

import re
from os import name as OS_NAME
from ipaddress import ip_address
from netifaces import interfaces
from Crypto.Random.random import randint
import argparse
import json
import sys
# Mininet imports
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Host, OVSKernelSwitch

CONFIG_DIRECTIVES = [
    'switches',
    'devices'
]

DEVICE_DIRECTIVES = [
    'interfaces',
    'iptables',
    'launcher',
    'name',
    'routes',
]

INTERFACE_DIRECTIVES = [
    'ip',
    'name',
    'mac',
    'switch'
]

def print_error(msg: str):
    sys.stderr.write(msg)
    sys.stderr.flush()

def next_dpid(sw: list[OVSKernelSwitch]) -> str:
    nxt = 1
    while nxt in [int(d.dpid, 16) for d in sw]:
        nxt += 1
    return f'{nxt:016x}'

def new_mac() -> str:
    mac = '00:' * 6
    while mac in ['00:' * 6, 'FF:' * 6]:
        mac = ''.join([f'{randint(i-i,255):02X}:' for i in range(6)])
    return mac[:-1]

MAC_REGEX = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
check_mac = lambda mac: bool(MAC_REGEX.match(mac) is not None) if isinstance(mac, str) else False

def nefics(conf: dict):
    # Check for mandatory configuration directives
    try:
        assert all(x in conf.keys() for x in CONFIG_DIRECTIVES)
    except AssertionError:
        print_error(f'Missing configuration directives: {[x for x in CONFIG_DIRECTIVES if x not in conf.keys()]}')
        sys.exit()
    # Initialize Mininet
    net = Mininet(topo=None, build=False, autoSetMacs=False)
    # Add SDN controller
    c0 = net.addController(name='c0') # TODO: Add the possibility of using an external controller
    # Setup virtual switches
    switches = dict[str, OVSKernelSwitch]()
    try:
        assert isinstance(conf['switches'], list)
        assert all(isinstance(x, dict) for x in conf['switches'])
        assert all('name' in x.keys() for x in conf['switches'])
        assert all(isinstance(x['name'], str) for x in conf['switches'])
        assert all(isinstance(x['dpid'], int) for x in conf['switches'] if 'dpid' in x.keys())
        assert len(set([sw['name'] for sw in conf['switches']])) == len(conf['switches']) # Unique switch names
        assert len(set([sw['dpid'] for sw in conf['switches'] if 'dpid' in sw.keys()])) == len([sw['dpid'] for sw in conf['switches'] if 'dpid' in sw.keys()]) # Unique DPID
    except AssertionError:
        print_error(f'Configured value for the "switches" directive is not a valid nefics switch set.\r\n')
        sys.exit()
    for s in conf['switches']:
        try:
            if 'dpid' in s.keys():
                assert f'{s["dpid"]:016x}' not in [x.dpid for x in switches.values()]
                switches[s['name']] = net.addSwitch(s['name'], dpid=f'{s["dpid"]:016x}', cls=OVSKernelSwitch)
            else:
                switches[s['name']] = net.addSwitch(s['name'], dpid=next_dpid(switches), cls=OVSKernelSwitch)
        except AssertionError:
            print_error(f'Bad switch definition: {str(s)}\r\n')
            sys.exit()
    # Setup virtual devices
    devices:dict[str, Host] = {}
    try:
        # Check types
        assert isinstance(conf['devices'], list)
        assert all(isinstance(dev, dict) for dev in conf['devices'])
        assert all(isinstance(i, dict) for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)
        # Check valid directives
        assert all(k in DEVICE_DIRECTIVES for dev in conf['devices'] for k in dev.keys())
        assert all(k in INTERFACE_DIRECTIVES for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc for k in i.keys())
        # Check required directives
        assert all(k in i.keys() for k in ['ip', 'name', 'switch'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)
        assert all(i['switch'] in [sw['name'] for sw in conf['switches']] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)
        # Check uniqueness, when applicable
        assert len(set([dev['name'] for dev in conf['devices']])) == len(conf['devices'])
        assert sum([len(set(i['name'] for i in ifc)) for ifc in [dev['interfaces'] for dev in conf['devices']]]) == sum([len([i['name'] for i in ifc]) for ifc in [dev['interfaces'] for dev in conf['devices']]])
        assert len(set(i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)) == len([i['ip'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc])
        assert len(set(i['mac'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc)) == len([i['mac'] for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc])
    except AssertionError:
        print_error(f'Bad definition in "devices" configuration directive\r\n')
        sys.exit()
    for dev in conf['devices']:
        hname = str(dev['name'])
        dhost = net.addHost(hname, cls=Host)
        devices[hname] = dhost
        for iface in dev['interfaces']:
            # Check MAC address
            ifmac = None
            if 'mac' in iface.keys() and check_mac(iface['mac']):
                ifmac = iface['mac']
            elif 'mac' in iface.keys():
                print_error(f'Bad MAC address: {iface["mac"]}. Generating random MAC address for this interface ...\r\n')
            if ifmac is None:
                ifmac = new_mac()
                while ifmac.upper() in ['00:00:00:00:00:00', 'FF:FF:FF:FF:FF:FF'] + [str(i['mac']).upper() for ifc in [dev['interfaces'] for dev in conf['devices']] for i in ifc]:
                    ifmac = new_mac()
            # Check IP address
            try:
                assert '/' in iface['ip']
                assert int(iface['ip'].split('/')[1]) <= 32
                assert int(iface['ip'].split('/')[1]) >= 0
                ip_address(iface['ip'].split('/')[0])
            except (ValueError, AssertionError):
                print_error(f'Bad IP address definition: {iface["ip"]}\r\n')
                sys.exit()
            # Create interface
            ln = net.addLink(dhost, switches[iface['switch']])
            niface = ln.intf1
            niface.rename(f'{hname}-{iface["name"]}')
            niface.setMAC(iface['mac'])
            niface.setIP(iface['ip'])
    # Check for host interface
    if 'localiface' in conf.keys():
        try:
            assert isinstance(conf['localiface'], dict)
            assert all(x in ['iface', 'switch'] for x in conf['localiface'].keys())
            assert all(isinstance(x, str) for x in conf['localiface'].values())
        except AssertionError:
            print_error(f'Bad localiface definition: {str(conf["localiface"])}\r\n')
            sys.exit()
        try:
            assert conf['localiface'] in interfaces()
        except AssertionError:
            print_error(f'Unknown local interface: "{conf["localiface"]}"\r\n')
            sys.exit()
    # Start network
    net.build()
    c0.start()
    for sw in switches.values():
        sw.start([c0])
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].attach(conf['localiface']['iface'])
    net.pingAll()
    # Launch instances
    CLI(net)
    if 'localiface' in conf.keys():
        switches[conf['localiface']['switch']].detach(conf['localiface']['iface'])
    net.stop()

if __name__ == '__main__':
    try:
        assert OS_NAME == 'posix'
    except AssertionError:
        print_error(f'ERROR: NEFICS needs a POSIX system\r\n')
        sys.exit()
    ap = argparse.ArgumentParser(description='NEFICS topology simulator')
    ap.add_argument('config', metavar='CONFIGURATION_FILE', type=argparse.FileType('r', encoding='utf-8'))
    config_file = ap.parse_args().config
    try:
        config = json.load(config_file)
    except json.decoder.JSONDecodeError:
        print_error(f'Error reading configuration: JSON decode error\r\n')
        sys.exit()
    nefics(config)

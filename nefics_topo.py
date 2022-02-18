#!/usr/bin/env python3

from os import system, environ
from signal import SIGTERM
from subprocess import PIPE, Popen
from mininet.net import Mininet
from mininet.node import Host
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Intf
from mininet.term import makeTerm

info('*** Initializing ***\n')
net = Mininet(topo=None, ipBase='10.0.0.0/24', build=False, autoSetMacs=False)
c0 = net.addController(name='c0')
sw = net.addSwitch('s1', dpid='0000000000000001', cls=OVSKernelSwitch)
info('*** Creating RTU hosts ***\n')
hsrc = net.addHost('hsrc', cls=Host, ip='10.0.0.10/24', mac='00:1f:f8:eb:4a:53')
htx = net.addHost('htx', cls=Host, ip='10.0.0.11/24', mac='00:1f:f8:a9:f2:97')
hload = net.addHost('hload', cls=Host, ip='10.0.0.12/24', mac='00:1f:f8:23:bd:1c')
info('*** Adding network links ***\n')
net.addLink(sw, hsrc)
net.addLink(sw, htx)
net.addLink(sw, hload)
info('*** Starting network ***\n')
net.build()
for c in net.controllers:
    c.start()
sw.start([c0])
hsrc.cmd('ip route add default via 10.0.0.1')
htx.cmd('ip route add default via 10.0.0.1')
hload.cmd('ip route add default via 10.0.0.1')
# Create host interface in mininet
system('sudo ip link add veth0 type veth peer name veth1')
system('sudo ip link set veth0 up')
system('sudo ip link set veth1 up')
system('sudo ovs-vsctl add-port s1 veth1')
system('sudo ip addr add 10.0.0.1/24 dev veth0')
net.pingAll()
net.terms += makeTerm(hsrc, cmd='python3 -m nefics.iec104devicelauncher -c ./conf/Source.json')
net.terms += makeTerm(htx, cmd='python3 -m nefics.iec104devicelauncher -c ./conf/Transmission.json')
net.terms += makeTerm(hload, cmd='python3 -m nefics.iec104devicelauncher -c ./conf/Load.json')
localxterm = Popen(['xterm', '-display', environ['DISPLAY']], stdout=PIPE, stdin=PIPE)
CLI(net)
localxterm.kill()
localxterm.wait()
system('sudo ovs-vsctl del-port s1 veth1')
system('sudo ip link del veth0')
net.stop()


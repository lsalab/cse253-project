#!/usr/bin/env python3

from mininet.topo import Topo

class MyTopo(Topo):

    def __init__(self):
        Topo.__init__(self)

        hosts = []
        for i in range(8):
            hosts.append(self.addHost('h' + str(i+1), ip='10.0.0.' + str(i+1) + '/24'))
        att = self.addHost('att', ip='10.0.0.100/24')
        hosts.append(att)

        sw = self.addSwitch('s1')

        for h in hosts:
            self.addLink(h, sw)
        self.addLink(att, sw)

topos = { 'mytopo': (lambda: MyTopo()) }

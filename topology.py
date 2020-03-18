#!/usr/bin/env python3

from mininet.topo import Topo

class MyTopo(Topo):

    def __init__(self):
        Topo.__init__(self)

        hosts = []
        for i in range(8):
            hosts.append(self.addHost('h' + str(i+1)))

        sw = self.addSwitch('s1')

        for h in hosts:
            self.addLink(h, sw)

topos = { 'mytopo': (lambda: MyTopo()) }

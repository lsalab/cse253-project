#!/usr/bin/env python3

from mininet.topo import Topo

class MyTopo(Topo):

    def __init__(self):
        Topo.__init__(self)

        rsrc = self.addHost('rsrc')
        rtrx = self.addHost('rtx')
        rlds = self.addHost('load')
        scad = self.addHost('scada')

        sw = self.addSwitch('s1')

        for h in [rsrc, rtrx, rlds, scad]:
            self.addLink(h, sw)

topos = { 'mytopo': (lambda: MyTopo()) }

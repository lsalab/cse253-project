#!/usr/bin/env python3

from struct import unpack
from scapy.fields import XByteField, LEShortField, StrField, PacketField
from scapy.packet import Packet, Padding, conf
from .const import *
from .ioa import IOAS, IOALEN
    
class ApciTypeI(Packet):

    name = 'APCI Type I'
    fields_desc = [
        XByteField('Type', 0x00),
        LEShortField('Tx', 0x0000),
        LEShortField('Rx', 0x0000)
    ]

    def do_dissect(self, s):
        self.Type = 0x00
        self.Tx = int((s[0] & 0xfe) / 2) + (s[1] * 0x80)
        self.Rx = int((s[2] & 0xfe) / 2) + (s[3] * 0x80)
        return s[4:]
    
    def do_build(self):
        s = list(range(4))  
        s[0] = (self.Tx << 1) & 0xfe
        s[1] = self.Tx >> 7
        s[2] = (self.Rx << 1) & 0xfe
        s[3] = self.Rx >> 7
        return s
    
    def __bytes__(self):
        return bytes(self.build())


class ApciTypeS(Packet):
    name = 'APCI Type S'
    fields_desc = [
        StrField('Type', None),
        LEShortField('Rx', 0x0000)
    ]

    def do_dissect(self, s):
        flags_Type = s[0] & 0x03
        self.Type = TYPE_APCI[flags_Type]
        self.Rx = int((s[2] & 0xfe) / 2) + (s[3] * 0x80)
        return s[4:]

    def dissect(self, s):
        s = self.pre_dissect(s)
        s = self.do_dissect(s)
        s = self.post_dissect(s)
        payl,pad = self.extract_padding(s)
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            self.add_payload(Padding(pad))

    def do_build(self):
        s = list(range(4))
        s[0] = 0x01
        s[1] = 0x00
        s[2] = (self.Rx & 0x7f) << 1 
        s[3] = (self.Rx >> 7) & 0xff
        return s
        

    def __bytes__(self):
        return bytes(self.build())

class ApciTypeU(Packet):
    name = 'APCI Type U'
    fields_desc = [
        XByteField('Type', None),
        XByteField('UType', None)
    ]

    def do_dissect(self, s):
        self.Type = s[0] & 0x03
        self.UType = (s[0] & 0xfc) >> 2
        return s[4:]

    def dissect(self, s):
        s = self.pre_dissect(s)
        s = self.do_dissect(s)
        s = self.post_dissect(s)
        payl,pad = self.extract_padding(s)
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            self.add_payload(Padding(pad))

    def do_build(self):
        s = list(range(4))
        s[0] = ((self.UType << 2) & 0xfc) | self.Type 
        s[1] = 0
        s[2] = 0
        s[3] = 0
        return s

    def __bytes__(self):
        return bytes(self.build())

class ApciType(StrField):

    def m2i(self, pkt, x):
        ptype = x[0] & 0x03
        if ptype in [0x00, 0x02]:
            return ApciTypeI(x)
        elif ptype == 0x01:
            return ApciTypeS(x)
        else:
            return ApciTypeU(x)

    def addfield(self, pkt, s, val):
        return s + self.i2m(pkt, val)
    
    def getfield(self, pkt, s):
        return s[4:], self.m2i(pkt, s[:4])
     
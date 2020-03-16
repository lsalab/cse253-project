#!/usr/bin/env python3

from struct import unpack, pack
from scapy.packet import Raw, bind_layers, Padding, Packet, conf
from scapy.layers.inet import TCP
from scapy.fields import XByteField, ByteField, PacketListField, ByteEnumField, PacketField
from .subPackets import ApciType
from .ioa import IOAS, IOALEN
from .const import SQ, CAUSE_OF_TX, TYPEID_ASDU
from scapy.all import conf

class ASDU(Packet):

    name = 'IEC 60870-5-104-Asdu'
    fields_desc = [
        ByteField('TypeId',None),
        ByteField('SQ',None),
        ByteField('NumIx',0),
        ByteEnumField('CauseTx',None, CAUSE_OF_TX),
        ByteField('Negative',False),
        ByteField('Test', None),
        ByteField('OA',None),
        ByteField('Addr',None),
        PacketListField('IOA', None)
    ]

    def do_dissect(self, s):
        try: # TODO: [Luis] How to use Try & Exception
            self.TypeId = s[0] & 0xff
        except Exception:
            if conf.debug_dissector:
                raise NameError('HiThere')
            self.TypeId = 'Error'
        typeId = s[0] & 0xff
        flags_SQ = s[1] & 0x80
        
        self.SQ =  flags_SQ
        self.NumIx = s[1] & 0x7f
        self.CauseTx = s[2] & 0x3F
        self.Negative = s[2] & 0x40
        self.Test = s[2] & 0x80
        self.OA = s[3]
        self.Addr = unpack('<H',s[4:6])[0]
        # self.Addr = s[4] # NOTE: For Malformed Packets TypeId = 13


        flag=True
        list_IOA = list()
        remain = s[6:]
        # remain = s[5:] # NOTE: For Malformed Packets TypeId = 13 
        
        idx=6
        # idx=5 # NOTE: For Malformed Packets TypeId = 13
        i=1
        typeIOA = IOAS[typeId]
        lenIOA=IOALEN[typeId]
        j=0
        if self.SQ:
            for i in range(1,self.NumIx+1):
                if flag:
                    list_IOA.append(typeIOA(remain[:lenIOA]))
                    offset= list_IOA[0].IOA
                    remain = remain[lenIOA:]
                    idx = idx+lenIOA
                    lenIOA = lenIOA-3
                else:
                    offsetIOA = pack("<H",(i-1)+offset)+b'\x00' # See 7.2.2.1 of IEC 60870-5-101 
                    remain2 = offsetIOA + remain[:lenIOA]
                    list_IOA.append(typeIOA(remain2))
                    remain = remain[lenIOA:]
                    idx = idx+lenIOA
                flag=False
        else:
            for i in range(1,self.NumIx+1):
                list_IOA.append(typeIOA(remain[:lenIOA])) 
                remain = remain[lenIOA:]
                idx= idx+lenIOA
        self.IOA = list_IOA
        return s[idx:]

    def extract_padding(self, s):
        return None, s

    def do_build(self):
        s = list(range(6))
        s[0] = self.TypeId
        s[1] = ((self.SQ << 7) & 0x80) | self.NumIx
        s[2] = self.Test << 7 | self.Negative << 6 | self.CauseTx
        s[3] = self.OA
        s[4] = (self.Addr & 0xff)
        s[5] = ((self.Addr >> 8) & 0xFF)
        if self.IOA is not None:
            for i in self.IOA:
                s += i.do_build()
        
        return s

    def __bytes__(self):
        return bytes(self.build())

class APCI(Packet):

    name = 'IEC 60870-5-104-Apci'

    fields_desc = [
        XByteField('START',0x68),
        ByteField('ApduLen',4),
        ApciType('Apci', None),
    ]

    def extract_padding(self, s):
        return None, s

class APDU(Packet):
    name = 'APDU'
    fields_desc = [
        PacketField('APCI', None, APCI),
        PacketField('ASDU', None, ASDU)
    ]

    def dissect(self, s):
        s = self.pre_dissect(s)
        s = self.do_dissect(s)
        s = self.post_dissect(s)
        payl,pad = self.extract_padding(s) 
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            if pad[0] in [0x68]: #TODO: [Luis] "self.underlayer is not None"
                self.add_payload(APDU(pad))
            else:
                self.add_payload(Padding(pad))

    def extract_padding(self, s):
        return '', s

bind_layers(TCP, APDU, sport=2404)
bind_layers(TCP, APDU, dport=2404)
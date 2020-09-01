#!/usr/bin/env python3

from struct import unpack
from scapy.fields import PacketField, LEShortField, ShortField, FlagsField, ByteEnumField, BitEnumField, BitField, XIntField
from .fields import IOAID, LEFloatField, ByteField, SignedShortField
from .const import QDS_FLAGS, SU, DOW_ENUM, SEL_EXEC, DPI_ENUM, DIQ_FLAGS, SIQ_FLAGS, TRANSIENT, QOI_ENUM, R_ENUM, I_ENUM, QU_ENUM, SEL_EXEC, SCS_ENUM
from scapy.packet import Packet

class COI(Packet):
    name = 'COI'
    fields_desc = [
        BitEnumField('I', None, 1, I_ENUM),
        BitEnumField('R', None, 7, R_ENUM),
        # ByteEnumField('R', None, R_ENUM),
        # ByteEnumField('I', None, I_ENUM),
    ]

class VTI(Packet):
    name = 'VTI'
    fields_desc = [
        BitEnumField('Transient', None, 1, TRANSIENT),
        BitField('Value', None, 7),
        # ByteField('Value',False),
        # ByteEnumField('Transient',None, TRANSIENT)
    ]

    # def do_dissect(self, s):
    #     self.Value = s[0] & 0x7f
    #     self.Transient = s[0] & 0x80

    #     return s[1:]

    # def do_build(self):
    #     s = list(range(1))
    #     s[0] = self.Transient | self.Value
        
    #     return bytes(s)
    
    # def extract_padding(self, s):
    #     return '', s

class DIQ(Packet):
    name = 'QDS'
    fields_desc = [
        ByteEnumField('DPI', 0x00, DPI_ENUM),
        FlagsField('flags', 0x00, 8, DIQ_FLAGS),
        # ByteField('BL',None),
        # ByteField('SB',None),
        # ByteField('NT',None),
        # ByteField('IV',None)
    ]

    def do_dissect(self, s):
        self.DPI = s[0] & 0x03
        self.flags = s[0] & 0xf0
        # self.BL = BL[s[0] & 0x10]
        # self.SB = SB[s[0] & 0x20]
        # self.NT = NT[s[0] & 0x40]
        # self.IV = IV[s[0] & 0x80]

        return s[1:]

    def do_build(self):
        s = list(range(1))
        # s[0] = (self.DPI & 0x11) | (self.BL << 4 & 0x10) | (self.SB << 5 & 0x20) | (self.NT << 6 & 0x40) | (self.IV << 7 & 0x80) 
        s[0] = self.DPI | self.flags
        
        return bytes(s)
    
    def extract_padding(self, s):
        return '', s

class QOS(Packet):
    name = 'QOS'
    fields_desc = [
        BitEnumField('SE', 0x00, 1, SEL_EXEC),
        BitField('QL', 0x00, 7),
        # ByteField('QL',False),
        # ByteEnumField('SE', 0x00, SEL_EXEC)
    ]

    # def do_dissect(self, s):
    #     self.QL = s[0] & 0x7F
    #     self.SE = s[0] & 0x80

    #     return s[1:]

    # def do_build(self):
    #     s = list(range(1))
    #     s[0] = (self.SE << 7 &  0x80) | (self.QL & 0x7F)
        
    #     return s

    # def __bytes__(self):
    #     return bytes(self.build())
    
    # def extract_padding(self, s):
    #     return '', s

class CP56Time(Packet):

    name = 'CP56Time'
    fields_desc = [
        LEShortField('MS', 0),
        BitField('IV', 0, 1),
        BitField('RES1', 0, 1),
        BitField('Min', 0, 6),
        BitField('SU', 0, 1),
        BitField('RES2', 0, 2),
        BitField('Hour', 0, 5),
        BitEnumField('DOW', 0, 3, DOW_ENUM),
        BitField('Day', 0, 5),
        BitField('RES3', 0, 4),
        BitField('Month', 0, 4),
        BitField('RES4', 0, 1),
        BitField('Year', 0, 7),
        # ByteField('MS',None),
        # ByteField('Min',None),
        # ByteField('IV',None),
        # ByteField('Hour',None),
        # ByteField('SU',None),
        # ByteField('Day',None),
        # ByteField('DOW',None),
        # ByteField('Month',None),
        # ByteField('Year',None),
    ]

    # def do_dissect(self, s):
    #     try:
    #         self.MS = unpack('<H',s[0:2])[0]
    #         self.Min = int(s[2] & 0x3f)
    #         self.IV = int(s[2] & 0x80)
    #         self.Hour = int(s[3] & 0x1F)
    #         self.SU = int(s[3] & 0x80)
    #         self.Day = int(s[4] & 0x1F)
    #         self.DOW = int(s[4] & 0xE0)
    #         self.Month = int(s[5] & 0x0F)
    #         self.Year = int(s[6] & 0x7F)
    #         return s[7:]
    #     except IndexError:
    #         self.MS = 0
    #         self.Min = 0
    #         self.IV = 0
    #         self.Hour = 0
    #         self.SU = 0
    #         self.Day = 0
    #         self.DOW = 0
    #         self.Month = 0
    #         self.Year = 0
    #         return bytes(b'')

    # def do_build(self):
    #     s = list(range(7))
    #     s[0] = self.MS & 0xFF
    #     s[1] = (self.MS >> 8) & 0xFF
    #     s[2] = (self.IV & 0x80) | (self.Min & 0x3F)
    #     s[3] = (self.SU & 0x80) | (self.Hour & 0x1F)
    #     s[4] = (self.DOW & 0xE0) | (self.Day & 0x1F)
    #     s[5] = self.Month & 0xF
    #     s[6] = (self.Year & 0x7F)
        
    #     return bytes(s)

    # def extract_padding(self, s):
    #     return '', s

class SCO(Packet):
    name = 'SCO'
    fields_desc = [
        BitEnumField('SE', 0, 1, SEL_EXEC),
        BitEnumField('QU', 0, 6, QU_ENUM),
        BitEnumField('SCS', 0, 1, SCS_ENUM),
        # ByteEnumField('SCS', 0x00, SCS_ENUM),
        # ByteEnumField('QU', None, QU_ENUM),
        # ByteEnumField('SE', None, SEL_EXEC)
    ]

    # def do_dissect(self, s):
    #     self.SCS = s[0] & 0x01
    #     self.QU = s[0] & 0x7C
    #     self.SE = s[0] & 0x80

    #     return s[1:]

    # def do_build(self):
    #     s = list(range(1))
    #     s[0] = self.SE | self.SCS | self.QU

    #     return s

    # def __bytes__(self):
    #     return bytes(self.build())
    
    # def extract_padding(self, s):
    #     return '', s

class IOA36(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        LEFloatField('Value', None),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
        PacketField('CP56Time', None, CP56Time),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA13(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        LEFloatField('Value', None),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA9(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        SignedShortField('Value', None),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA50(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        LEFloatField('Value', None),
        PacketField('QOS', None, QOS)
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA3(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('DIQ', None, DIQ)
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA5(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('VTI', None, VTI),
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA100(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        ByteEnumField('QOI', None, QOI_ENUM),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA103(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('CP56Time', None, CP56Time)
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA30(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        FlagsField('SIQ', 0x00, 8, SIQ_FLAGS),
        PacketField('CP56Time', None, CP56Time)
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA70(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('COI', None, COI),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA31(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('DIQ', None, DIQ),
        PacketField('CP56Time', None, CP56Time)
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA1(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        FlagsField('SIQ', 0x00, 8, SIQ_FLAGS),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA7(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        # PacketField('BSI', None, BSI),
        XIntField('BSI', 0x00000000),
        # PacketField('QDS', None, QDS_FLAGS)
        FlagsField('QDS', 0x00, 8, QDS_FLAGS),
    ]

    # def extract_padding(self, s):
    #     return '', s

class IOA45(Packet):
    name = 'IOA'
    fields_desc = [
        IOAID('IOA', None),
        PacketField('SCO', None, SCO)
    ]

    # def extract_padding(self, s):
    #     return '', s

IOAS = {
    36: IOA36,
    13: IOA13,
    9: IOA9,
    50: IOA50,
    3: IOA3,
    5: IOA5,
    100: IOA100,
    103: IOA103,
    30: IOA30,
    70: IOA70,
    31: IOA31,
    1: IOA1,
    7: IOA7,
    45: IOA45,
}

IOALEN = {
    36: 15,
    #13: 7, # NOTE: For INFORMATION OBJECT ADDRESS of two octets 
    13: 8,
    9: 6,
    50: 8,
    3: 4,
    5: 5,
    100: 4,
    103: 10, # NOTE: For INFORMATION OBJECT ADDRESS of two octets
    # 30: 11, 
    30: 10,
    70: 4,
    31: 11,
    1: 4,
    7: 8,
    45: 4,
}

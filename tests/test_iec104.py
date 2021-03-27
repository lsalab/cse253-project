#!/usr/bin/env python3

from nefics.IEC104.dissector import APDU, APCI, ASDU
from nefics.IEC104.ioa import DIQ, IOA3

def test_TESTFR_actcon():
    apdu = APDU(b'\x68\x04\x83\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x20

def test_TESTFR_act ():
    apdu = APDU(b'\x68\x04\x43\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x10

def test_STOPDT_actcon():
    apdu = APDU(b'\x68\x04\x23\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x08

def test_STOPDT_act():
    apdu = APDU(b'\x68\x04\x13\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x04

def test_STARTDT_actcon():
    apdu = APDU(b'\x68\x04\x0b\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x02

def test_STARTDT_act():
    apdu = APDU(b'\x68\x04\x07\x00\x00\x00')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x03
    assert apci.UType   == 0x01

def test_SFrame():
    apdu = APDU(b'\x68\x04\x01\x00\x3e\x22')
    assert apdu.haslayer('APCI')
    apci = apdu['APCI']
    assert isinstance(apci, APCI)
    assert apci.ApduLen == 0x04
    assert apci.Type    == 0x01
    assert apci.Rx      == 0x111f

def test_asdu_type3():
    apdu = APDU(b'\x68\x0e\x1c\x00\x08\x00\x03\x01\x03\x00\x0a\x00\x65\x00\x00\x02')
    assert False not in [apdu.haslayer(x) for x in ['APCI', 'ASDU', 'IOA3', 'DIQ']]
    apci = apdu['APCI']
    asdu = apdu['ASDU']
    ioa = apdu['IOA3']
    diq = apdu['DIQ']
    assert isinstance(apci, APCI)
    assert isinstance(asdu, ASDU)
    assert isinstance(ioa, IOA3)
    assert isinstance(diq, DIQ)
    assert apci.ApduLen == 14
    assert apci.Type == 0x00
    assert apci.Tx == 14
    assert apci.Rx == 4
    assert asdu.TypeId == 3
    assert asdu.SQ == 0
    assert asdu.NumIx == 1
    assert asdu.CauseTx == 3
    assert asdu.Test == 0x00
    assert asdu.OA == 0x00
    assert asdu.Addr == 10
    assert ioa.IOA == 101
    assert diq.DPI == 0x02

def test_asdu_type36():
    apdu = APDU(b'\x68\x19\x6c\x00\x94\x00\x24\x01\x03\x00\x21\x00\xc9\x04\x00\x58\xfd\x79\x41\x00\x6f\x33\x09\x16\x78\x03\x15')
    assert apdu.haslayer('APCI')
    assert apdu.haslayer('ASDU')
    assert apdu.haslayer('IOA36')
    apci = apdu['APCI']
    asdu = apdu['ASDU']
    ioa = apdu['IOA36']
    assert apci.ApduLen == 25
    assert apci.Type == 0x00
    assert apci.Tx == 54
    assert apci.Rx == 74
    assert asdu.TypeId == 36
    assert asdu.SQ == 0
    assert asdu.NumIx == 1
    assert asdu.Test == 0
    assert asdu.CauseTx == 3
    assert asdu.OA == 0
    assert asdu.Addr == 33
    assert ioa.IOA == 1225
    assert str(round(ioa.Value, 2)) == '15.62'


#!/usr/bin/env python3

# Scapy imports
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP

BASE_PKT = Ether(
    src="08:00:27:5d:b8:b6",
    dst="08:00:27:64:66:73",
    type=0x0800
)/IP(
    src="192.168.56.5",
    dst="192.168.56.10",
    id=0x0052,
    flags=0x40,
    ttl=128,
    proto=6
)/TCP(
    sport=42568,
    dport=102,
    seq=124,
    ack=24,
    flags=0x018,
    window=64240
)

# IEC-61850
import nefics.IEC61850.iec61850_mms as iec61850
from nefics.IEC61850.iec61850_mms.tpkt import TPKT
iec61850.bind_layers()

def test_connection_request():
    mms = BASE_PKT/TPKT(b"\x03\x00\x00\x16\x11\xe0\x00\x00\x00\x01\x00\xc1\x02\x00\x00\xc2\x02\x00\x01\xc0\x01\x0a")
    mms.show2()
    # Check layers
    assert mms.haslayer('TPKT')
    assert mms.haslayer('COTP')
    assert mms.haslayer('COTP_CR')
    # Check TPKT values
    assert mms['TPKT'].getfieldval('version') == 3
    assert mms['TPKT'].getfieldval('length')  == 22
    # Check COTP headers
    assert mms['COTP_CR'].getfieldval('length') == 17
    assert (mms['COTP_CR'].getfieldval('TPDU') << 4) == 0xe0
    assert mms['COTP_CR'].getfieldval('destination_reference') == 0x0000
    assert mms['COTP_CR'].getfieldval('source_reference') == 0x0001
    assert mms['COTP_CR'].getfieldval('class') == 0
    assert bool(mms['COTP_CR'].getfieldval('extended_format')) is False
    assert bool(mms['COTP_CR'].getfieldval('explicit')) is False
    # Check COTP parameters
    cotp_params = mms['COTP_CR'].getfieldval('parameters')
    assert len(cotp_params) == 3
    assert cotp_params[0].getfieldval('code') == 0xc1
    assert cotp_params[0].getfieldval('length') == 0x02
    assert cotp_params[0].getfieldval('value') == b"\x00\x00"
    assert cotp_params[1].getfieldval('code') == 0xc2
    assert cotp_params[1].getfieldval('length') == 0x02
    assert cotp_params[1].getfieldval('value') == b"\x00\x01"
    assert cotp_params[2].getfieldval('code') == 0xc0
    assert cotp_params[2].getfieldval('length') == 0x01
    assert cotp_params[2].getfieldval('value') == 0x0a

def test_connection_confirmation():
    mms = BASE_PKT/TPKT(b"\x03\x00\x00\x16\x11\xd0\x00\x01\x00\x04\x00\xc2\x02\x00\x01\xc1\x02\x00\x00\xc0\x01\x0a")
    # Check layers
    assert mms.haslayer('TPKT')
    assert mms.haslayer('COTP')
    assert mms.haslayer('COTP_Connection_Confirm')
    # Check TPKT values
    assert mms['TPKT'].getfieldval('version') == 3
    assert mms['TPKT'].getfieldval('length')  == 22
    # Check COTP headers
    assert mms['COTP_Connection_Confirm'].getfieldval('length') == 17
    assert mms['COTP_Connection_Confirm'].getfieldval('tpdu_code') == 0xd0
    assert mms['COTP_Connection_Confirm'].getfieldval('destination_reference') == 0x0001
    assert mms['COTP_Connection_Confirm'].getfieldval('source_reference') == 0x0004
    assert mms['COTP_Connection_Confirm'].getfieldval('class') == 0
    assert bool(mms['COTP_Connection_Confirm'].getfieldval('extended_format')) is False
    assert bool(mms['COTP_Connection_Confirm'].getfieldval('explicit')) is False
    # Check COTP parameters
    cotp_params = mms['COTP_Connection_Confirm'].getfieldval('parameters')
    assert cotp_params[0].getfieldval('code') == 0xc2
    assert cotp_params[0].getfieldval('length') == 0x02
    assert cotp_params[0].getfieldval('value') == b"\x00\x01"
    assert cotp_params[1].getfieldval('code') == 0xc1
    assert cotp_params[1].getfieldval('length') == 0x02
    assert cotp_params[1].getfieldval('value') == b"\x00\x00"
    assert cotp_params[2].getfieldval('code') == 0xc0
    assert cotp_params[2].getfieldval('length') == 0x01
    assert cotp_params[2].getfieldval('value') == b"\x0a"


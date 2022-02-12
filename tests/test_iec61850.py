#!/usr/bin/env python3

# Scapy imports
from scapy.packet import Packet, Raw
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
    # Check layers
    assert mms.haslayer('TPKT')
    assert mms.haslayer('COTP')
    assert mms.haslayer('COTP_Connection_Request')
    # Check TPKT values
    assert mms['TPKT'].getfieldval('version') == 3
    assert mms['TPKT'].getfieldval('length')  == 22
    # Check COTP headers
    assert mms['COTP_Connection_Request'].getfieldval('length') == 17
    assert mms['COTP_Connection_Request'].getfieldval('tpdu_code') == 0xe0
    assert mms['COTP_Connection_Request'].getfieldval('destination_reference') == 0x0000
    assert mms['COTP_Connection_Request'].getfieldval('source_reference') == 0x0001
    assert mms['COTP_Connection_Request'].getfieldval('class') == 0
    assert bool(mms['COTP_Connection_Request'].getfieldval('extended_format')) is False
    assert bool(mms['COTP_Connection_Request'].getfieldval('explicit')) is False
    # Check COTP parameters
    cotp_params = mms['COTP_Connection_Request'].getfieldval('parameters')
    assert len(cotp_params) == 3
    assert cotp_params[0].getfieldval('code') == 0xc1
    assert cotp_params[0].getfieldval('length') == 0x02
    assert cotp_params[0].getfieldval('value') == b"\x00\x00"
    assert cotp_params[1].getfieldval('code') == 0xc2
    assert cotp_params[1].getfieldval('length') == 0x02
    assert cotp_params[1].getfieldval('value') == b"\x00\x01"
    assert cotp_params[2].getfieldval('code') == 0xc0
    assert cotp_params[2].getfieldval('length') == 0x01
    assert cotp_params[2].getfieldval('value') == b"\x0a"

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

if __name__ == '__main__':
    mms = TPKT(
        b"\x03\x00\x00\xd3\x02\xf0\x80\x0d\xca\x05\x06\x13\x01\x00\x16\x01\x02\x14\x02\x00\x02\x33\x02\x00\x01\x34\x02\x00\x01\xc1\xb4\x31\x81\xb1\xa0\x03\x80\x01\x01\xa2\x81\xa9\x81\x04\x00\x00\x00\x01\x82\x04\x00\x00\x00\x01\xa4\x23\x30\x0f\x02\x01\x01\x06\x04\x52\x01\x00\x01\x30\x04\x06\x02\x51\x01\x30\x10\x02\x01\x03\x06\x05\x28\xca\x22\x02\x01\x30\x04\x06\x02\x51\x01\x61\x76\x30\x74\x02\x01\x01\xa0\x6f\x60\x6d\xa1\x07\x06\x05\x28\xca\x22\x02\x03\xa2\x07\x06\x05\x29\x01\x87\x67\x01\xa3\x03\x02\x01\x0c\xa4\x03\x02\x01\x00\xa5\x03\x02\x01\x00\xa6\x06\x06\x04\x29\x01\x87\x67\xa7\x03\x02\x01\x0c\xa8\x03\x02\x01\x00\xa9\x03\x02\x01\x00\xbe\x33\x28\x31\x06\x02\x51\x01\x02\x01\x03\xa0\x28\xa8\x26\x80\x03\x00\xfd\xe8\x81\x01\x0a\x82\x01\x0a\x83\x01\x05\xa4\x16\x80\x01\x01\x81\x03\x05\xf1\x00\x82\x0c\x03\xee\x1c\x00\x00\x04\x08\x00\x00\x79\xef\x18"
    )
    mms.show2()

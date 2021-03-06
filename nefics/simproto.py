#!/usr/bin/env python3

from scapy.packet import Packet
from scapy.fields import LEIntField, LEIntEnumField
from nefics.IEC104.fields import LEFloatField

SIM_PORT = 20202

'''
Simulation physical data format for UDP frames

Each frames carries up to two integer values and two floating point values. As frames are initially
sent to the broadcast address, each one should include a sender ID and a destination ID, both being
integer values. In addition, each frame must include a message ID, which determines the type of data
that is being included in the frame. The frames are comprised of 28 bytes carrying the 7 values in
little-endian encoding. If a value for a particular frame is not needed, there should be a zero in
its place.

28          25            21           17             13             9            5            0
[ Sender ID | Receiver ID | Message ID | Integer arg0 | Integer arg1 | Float arg0 | Float arg1 ]

'''
DATA_FMT = '<5I2f'
DATA_LEN = 28
QUEUE_SIZE = 1048576 # 1MB

'''
Message ID

To include additional messages, override the contents
with a Python fully qualified access path:

import nefics.simproto

nefics.simproto.MESSAGE_ID['MY_NEW_MESSAGE'] = <Integer value>
nefics.simproto.MESSAGE_ID_MAP[<Integer value>] = 'MY_NEW_MESSAGE'

It is important to add the new message to both dictionaries.
'''
MESSAGE_ID = {
    'MSG_WERE': 0,              # Query the IP address of a specific device
    'MSG_ISAT': 1,              # Reply a query for a device, providing the IP address as part of the IP stack
    'MSG_GETV': 2,              # Request a single voltage value
    'MSG_VOLT': 3,              # Reply a single voltage value request
    'MSG_GREQ': 4,              # Request equivalent load
    'MSG_TREQ': 5,              # Reply equivalent load value
    'MSG_NRDY': 0xFFFFFFFE,     # Device not ready (Incomplete initialization)
    'MSG_UKWN': 0xFFFFFFFF      # Unknown message received
}
MESSAGE_ID_MAP = {
    0x00000000: 'MSG_WERE',
    0x00000001: 'MSG_ISAT',
    0x00000002: 'MSG_GETV',
    0x00000003: 'MSG_VOLT',
    0x00000004: 'MSG_GREQ',
    0x00000005: 'MSG_TREQ',
    0xFFFFFFFE: 'MSG_NRDY',
    0xFFFFFFFF: 'MSG_UKWN'
}

class NEFICSMSG(Packet):

    name = 'NEFICS simulation message'

    fields_desc = [
        LEIntField('SenderID', 0),
        LEIntField('ReceiverID', 0),
        LEIntEnumField('MessageID', 0xFFFFFFFF, MESSAGE_ID_MAP),
        LEIntField('IntegerArg0', 0),
        LEIntField('IntegerArg1', 0),
        LEFloatField('FloatArg0', 0.0),
        LEFloatField('FloatArg1', 0.0)
    ]

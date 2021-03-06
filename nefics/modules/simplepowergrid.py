#!/usr/bin/env python3
'''
This module implements three types of devices in a simple resistive powergrid.

Each device can have at most two physical neighbors (One input, one output).

The powergrid topology is a simple resistive powergrid comprised of a power
source, transmission substations, and a consumer load.

The source acts as the generator and is linked to one transmission substation.

A transmission substation has a input neighbor, which provides the input voltage;
and an output neighbor, to which the output voltage is supplied..

The consumer load has one transmission substation as its input.
'''

from nefics.IEC104.dissector import *
from nefics.IEC104.ioa import *

# NEFICS imports
import nefics.modules.devicebase as devicebase
import nefics.simproto as simproto

BASE_IOA = 1001

class Source(devicebase.IEDBase):
    '''
    Source device.

    Only needs to answer for the supplied voltage.

    For any incomming NEFICS requests, it will only answer to its neighbor.

    The value polling returns a single APDU with a type 36 (M_ME_TF_1) ASDU
    containing the voltage.
    '''

    def __init__(self, guid, neighbors_in=list(), neighbors_out=list(), **kwargs):
        assert all(val is not None for val in [guid, neighbors_out])
        assert all(isinstance(val, int) for val in neighbors_out)
        assert len(neighbors_out) >= 1
        assert 'voltage' in kwargs
        assert isinstance(kwargs['voltage'], float)
        super().__init__(guid, neighbors_in=[], neighbors_out=neighbors_out[:1])
        self._voltage = kwargs['voltage']
    
    def handle_specific(self, message):
        if message.SenderID in self._n_out_addr.keys():
            addr = self._n_out_addr[message.SenderID]
            if message.MessageID == simproto.MESSAGE_ID['MSG_GETV']:
                pkt = simproto.NEFICSMSG(
                    SenderID=self.guid,
                    ReceiverID=message.SenderID,
                    MessageID=simproto.MESSAGE_ID['MSG_VOLT'],
                    FloatArg0=self._voltage
                )
            else:
                pkt = simproto.NEFICSMSG(
                    SenderID=self.guid,
                    ReceiverID=message.SenderID,
                    MessageID=simproto.MESSAGE_ID['MSG_UKWN']
                )
            self._sock.sendto(pkt.build(), addr)
    
    def poll_values_IEC104(self):
        ct = devicebase.cp56time()
        ioa = IOA36(IOA=BASE_IOA, Value=self._voltage, QDS=0, CP56Time=ct)
        pkt = APDU()
        pkt /= APCI(ApduLen=25, Type=0x00, tx=self.tx, Rx=self.rx)
        pkt /= ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=3, Test=0, OA=0, Addr=self.guid, IOA=[ioa])
        self.tx += 1
        return [pkt]

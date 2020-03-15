#!/usr/bin/env python3

from IEC104_Raw.dissector import ASDU, APCI, APDU
from IEC104_Raw.subPackets import ApciTypeI


class IEC104():

    def __init__(self, typeASDU, ioa):
        self.typeASDU = typeASDU
        self.ioa = ioa

    

    def get_tx(self):
        #TODO: define TX variable
        return 28050

    def get_rx(self):
         #TODO: define TX variable
        return 1

    def get_apci(self):
        start = 104
        apdulen = 25
        type_asdu = 0
        tx = self.get_tx()
        rx = self.get_rx()
        apci = ApciTypeI(Type = type_asdu, Tx = tx, Rx = rx)
        return APCI(START = start, ApduLen = apdulen, Apci = apci)

    def get_ioa36(self, measurement):
        # TODO: get_ioa36
        return 0

    def get_ioa3(self, status):
        # TODO: get_ioa36
        return

    def get_asdu(self, dato=None):
        TYPE_ASDU = {
            36 : self.get_ioa36,
            3: self.get_ioa3
            }
        if dato is None:
            raise NotImplementedError()
        
        typeId = 36
        sq = 0
        numix = 1
        causeTx = 1
        negative = 0
        test = 0
        oa = 1
        addr = 2
        ioa = TYPE_ASDU[self.typeASDU](dato)

        return ASDU(TypeId = typeId, SQ = sq, NumIx = numix, CauseTx = causeTx, Negative = negative, Test = test, OA = oa, Addr = addr, IOA = ioa)

    def get_pack(self, dato):

        apci = self.get_apci()

        if self.typeASDU == 36:
            asdu = self.get_asdu(dato)
        elif self.typeASDU == 3:
            asdu = self.get_asdu(dato)
        
        return APDU(APCI = apci, ASDU = asdu)
        

    def get_unPack(self, paquete):
        pass

if __name__ == '__main__':
    rtu = IEC104(36,1001)
    
    apci = rtu.get_pack(123)
    print(apci)

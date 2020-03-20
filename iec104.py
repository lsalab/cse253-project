#!/usr/bin/env python3

from IEC104_Raw.dissector import ASDU, APCI, APDU
from IEC104_Raw.subPackets import ApciTypeI
from IEC104_Raw.ioa import CP56Time, QDS, IOA36, IOA3, DIQ, IOA50, QOS
import time
from datetime import datetime

APDULEN_3 = 14
APDULEN_50 = 18
APDULEN_36 = 25

class IEC104():
    def __init__(self, typeASDU: int, ioa: int):
        self.typeASDU = typeASDU
        self.ioa = ioa

    def cp56time(self):
            now = datetime.now()
            ms = now.second*1000 + int(now.microsecond/1000)
            minu = now.minute
            iv = 0
            hour = now.hour
            su = 0
            day = now.day
            dow = now.today().weekday() + 1
            month = now.month
            year = now.year - 2000
            output = CP56Time(MS = ms, Min = minu, IV = iv, Hour = hour, SU = su, Day = day, DOW = dow, Month = month, Year = year)
            return output

    def get_apdu(self, dato: float, tx: int, rx: int, causeTx:int =1) -> bytes:
        
        

        if self.typeASDU == 36:
            apci = APCI(ApduLen=APDULEN_36, Apci=ApciTypeI(Tx=tx, Rx=rx))
            asdu = ASDU(TypeId=36, SQ=0, NumIx=1, CauseTx=1, Test=0, OA=1, Addr=2, IOA=IOA36(IOA=self.ioa, Value=dato, QDS=QDS(BL=0, SB=0, NT=0, IV=0), CP56Time=self.cp56time()))
        elif self.typeASDU == 3:
            apci = APCI(ApduLen=APDULEN_3, Apci=ApciTypeI(Tx=tx, Rx=rx))
            asdu =  ASDU(TypeId=3, SQ=0, NumIx=1, CauseTx=1, Test=0, OA=1, Addr=2, IOA=IOA3(IOA=self.ioa, DIQ = DIQ(DPI = int(dato), BL=0, SB=0, NT=0, IV=0)))
        elif self.typeASDU == 50:
            apci = APCI(ApduLen=APDULEN_50, Apci=ApciTypeI(Tx=tx, Rx=rx))
            asdu = ASDU(TypeId=50, SQ=0, NumIx=1, CauseTx=causeTx, Test=0, OA=1, Addr=2, IOA=IOA50(IOA=self.ioa, Value = int(dato), QOS = QOS(QL = 0, SE= 0) ))
        return bytes(APDU(APCI=apci, ASDU=asdu))

def get_command(pkt: APDU) -> dict:

    if pkt.haslayer('IOA50'):
        ioa = pkt['IOA50'].IOA
        valor = pkt['IOA50'].Value
    elif pkt.haslayer('IOA3'):
        ioa = pkt['IOA3'].IOA
        valor = pkt['DIQ'].DPI
    elif pkt.haslayer('IOA36'):
        ioa = pkt['IOA36'].IOA
        valor = pkt['IOA36'].Value
    elif pkt.haslayer('IOA'):
        ioa = pkt['IOA'].IOA
        valor = pkt['IOA'].Value
    else:
        ioa = 0
        valor = -1
    if pkt.haslayer('APCI'):
        tx = pkt['APCI'].Apci['ApciTypeI'].Tx
        rx = pkt['APCI'].Apci['ApciTypeI'].Rx
    else:
        tx = 0
        rx = 0
    
    return {'ioa':ioa,
    'tx':tx,
    'rx':rx,
    'value':valor}



if __name__ == '__main__':

    V = IEC104(36, 1001)

    apdu = i104.get_apdu(1, 28512, 1,7)

    # apdu.show()
    print(apdu['IOA50'].IOA)
    print(apdu['APCI'].Apci['ApciTypeI'].Tx)
    print(apdu['APCI'].Apci['ApciTypeI'].Rx)
    print(apdu['IOA50'].Value)

    datos = i104.get_command(apdu)
    print(datos['valor'])
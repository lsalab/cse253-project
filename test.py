from IEC104_Raw import *
from binascii import unhexlify
from IEC104_Raw.dissector import ASDU, APCI, APDU
from IEC104_Raw.subPackets import ApciTypeU
from IEC104_Raw.const import *


#hexdata = '680e000000002d010700640005000081'
# hexdata = '2d010700640005000081'
#data = unhexlify(hexdata)
# dissector.ASDU(data)
#APCI(data).show()

# pkt.show()
APCI(b'\x68\x04\x07\x00\x00\x00').show()
APCI(b'\x68\x0e\x10\x00\x02\x00').show()
APCI(b'\x68\x04\x01\x00\x06\x00').show()

#pkt.show()


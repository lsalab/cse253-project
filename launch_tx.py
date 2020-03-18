#!/usr/bin/env

import sys
from threading import Thread
from time import sleep
from rtu import Transmission, RTU_TRANSMISSION
from simcomm import SimulationHandler

if __name__ == '__main__':
    srtu = Transmission(
        guid=int(sys.argv[2]),
        type=RTU_TRANSMISSION,
        state=7,
        loads = [0.394737, 0.394737, 0.394737],
        left=int(sys.argv[3]),
        right=int(sys.argv[4]),
        confok=False
    )
    hrtu = SimulationHandler(srtu)
    mloop = Thread(target=srtu.loop)
    mloop.start()
    hrtu.start()
    print('Transmission RTU - ID: %d' % srtu.guid)
    while not hrtu.terminate:
        try:
            if all(x is not None for x in [srtu.vin, srtu.vout, srtu.rload, srtu.amp]):
                print('\rVin: {0:5.3f} V\tR: {2:5.3f} Ohm\tVout: {1:5.3f} V\tLoad: {3:5.3f} Ohm\tI: {4:5.3f} A'.format(srtu.vin, srtu.vout, srtu.load, srtu.rload, srtu.amp), end='')
            sleep(1)
        except KeyboardInterrupt:
            hrtu.terminate = True
            srtu.terminate = True
    print('')
    mloop.join()
    hrtu.join()

#!/usr/bin/env

import sys
from threading import Thread
from time import sleep
from rtu import Load, RTU_LOAD
from simcomm import SimulationHandler

if __name__ == '__main__':
    srtu = Load(guid=int(sys.argv[2]), type=RTU_LOAD, load=12.5, left=int(sys.argv[3]))
    hrtu = SimulationHandler(srtu)

    mloop = Thread(target=srtu.loop)
    mloop.start()
    hrtu.start()
    print('Load RTU - ID: %d' % srtu.guid)
    while not hrtu.terminate:
        try:
            if srtu.vin is not None:
                print('\rVin: {0:5.3f} V\tR: {1:5.3f} Ohm'.format(srtu.vin, srtu.load), end='')
            sleep(1)
        except KeyboardInterrupt:
            hrtu.terminate = True
            srtu.terminate = True
    print('')
    mloop.join()
    hrtu.join()

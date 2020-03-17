#!/usr/bin/env

from threading import Thread
from time import sleep
from rtu import Source, RTU_SOURCE
from simcomm import SimulationHandler

if __name__ == '__main__':
    srtu = Source(guid=1, type=RTU_SOURCE, voltage=500.0)
    hrtu = SimulationHandler(srtu)

    mloop = Thread(target=srtu.loop)
    mloop.start()
    hrtu.start()
    print('Source RTU - ID: %d' % srtu.guid)
    while not hrtu.terminate:
        try:
            print('\rVout: {0:5.3f} V'.format(srtu.voltage), end='')
            sleep(1)
        except KeyboardInterrupt:
            hrtu.terminate = True
            srtu.terminate = True
    print('')
    mloop.join()
    hrtu.join()

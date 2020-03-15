#!/usr/bin/env

import code
from rtu import Transmission, RTU_TRANSMISSION
from simcomm import SimulationHandler

srtu = Transmission(
    guid=2,
    type=RTU_TRANSMISSION,
    state=7,
    loads = [12.0, 10.0, 13.0],
    left=1,
    right=3
)
hrtu = SimulationHandler(srtu)
code.interact(local=locals())

#!/usr/bin/env

import code
from rtu import Load, RTU_LOAD
from simcomm import SimulationHandler

srtu = Load(guid=3, type=RTU_LOAD, load=100.0, left=2)
hrtu = SimulationHandler(srtu)
code.interact(local=locals())

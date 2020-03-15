#!/usr/bin/env

import code
from rtu import Source, RTU_SOURCE
from simcomm import SimulationHandler

srtu = Source(guid=1, type=RTU_SOURCE, voltage=500.0)
hrtu = SimulationHandler(srtu)
code.interact(local=locals())

#!/usr/bin/env python3

from subprocess import PIPE
from mininet.net import Mininet
from mininet.node import Host
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Intf

def main():
    '''main'''

    info('*** Initializing ***\n')
    net = Mininet(topo=None, ipBase='10.0.0.0/24', build=False, autoSetMacs=False)
    c0 = net.addController(name='c0')
    sw = net.addSwitch('s1', dpid='0000000000000001', cls=OVSKernelSwitch)
    Intf('eth2', node=sw)
    info('*** Creating RTU hosts ***\n')
    scada = net.addHost('scada', cls=Host, ip='10.0.0.2/24', mac='00:80:11:22:33:44')
    hsrc = net.addHost('hsrc', cls=Host, ip='10.0.0.10/24', mac='00:1f:f8:eb:4a:53')
    htx = net.addHost('htx', cls=Host, ip='10.0.0.11/24', mac='00:1f:f8:a9:f2:97')
    hload = net.addHost('hload', cls=Host, ip='10.0.0.12/24', mac='00:1f:f8:23:bd:1c')
    info('*** Adding network links ***\n')
    net.addLink(sw, scada)
    net.addLink(sw, hsrc)
    net.addLink(sw, htx)
    net.addLink(sw, hload)
    info('*** Starting network ***\n')
    net.build()
    for c in net.controllers:
        c.start()
    net.get('s1').start([c0])
    net.pingAll()
    info('*** Starting RTUs ***\n')
    hsrc_proc = hsrc.popen('python3 launch_src.py 1 &')
    htx_proc = htx.popen('python3 launch_tx.py 2 1 3 &')
    hload_proc = hload.popen('python3 launch_load.py 3 2 &')

    CLI(net)

    info('*** Terminating ***\n')
    htx_proc.kill()
    hload_proc.kill()
    hsrc_proc.kill()
    net.stop()
    

if __name__ == '__main__':
    setLogLevel('info')
    main()

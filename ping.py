#!/usr/bin/env python

# ping.py
#

import subprocess

def ping_node(address):
	try:
		ping_response = subprocess.check_call(["/bin/ping", "-c1", "-w2", address], stdout=subprocess.PIPE)
		return ping_response
	except:
		return -1

if __name__ == '__main__':
	addresses = []
	addresses.append("8.8.8.8")
	addresses.append("75.75.75.75")
	addresses.append("192.168.1.1")
	for a in addresses:
		r = ping_node(a)
		print "result = ", r

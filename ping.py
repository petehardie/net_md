#!/usr/bin/env python

# ping.py
#
# issues:
# how to handle an outage that never comes back?
# 	report status at the 24 hr mark for each node
#

import subprocess
import datetime
import time
import Queue
import logging
import threading

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%threadName)-10s) %(message)s',)

timeout = { True : 60, False : 5 } # timeout for when up, and when down
#reportTimeout = 24 * 60 * 60
reportTimeout = 60

outages = Queue.Queue() # the queue of outage reports

reportDir = "./reports"

class Outage:
	def __init__(self, ip, down, up):
		self.ip = ip # IP address
		self.down = down # time connection went down
		self.up = up # time connection was restored

	def getIp(self):
		return self.ip

	def getDown(self):
		return self.down

	def getUp(self):
		return self.up

class Node:
	def __init__(self, address, queue):
		self.address = address
		self.connected = True
		self.downAt = 0
		self.outages = queue # holder for the global

	def getIp(self):
		return self.address

	def ping(self):
		try:
			ping_response = subprocess.check_call(["/bin/ping", "-c1", "-w1", self.address], stdout=subprocess.PIPE)
			if self.connected == False:
				self.connected = True
				# record the outage
				self.outages.put(Outage(self.address, self.downAt, time.time()))
		except:
			if self.connected == True:
				self.connected = False
				self.downAt = time.time()
		return self.connected

def load_nodes(filename):
	array = []
	with open(filename) as f:
		for line in f:
			array.append(Node(line.strip(), outages))
	return array

# called to be the thread function, passed a node
def monitor(node):
	while True:
		time.sleep(timeout[node.connected])
		node.ping()

# called to read the outages from the queue and generate a report file
# includes the current state of each node
def report(queue, nodes):
	while True:
		time.sleep(24 * 60 * 60) # sleep 24 hours
		write_report(queue, nodes)

def write_report(queue, nodes):
		# generate filename from date
		d = datetime.date.today()
		filename = str(d.year) + str(d.month) + str(d.day)
		path = reportDir + '/' + filename
		f = open(path, 'w')
		# report on the node status
		for n in nodes:
			f.write('Node ' + n.getIp() + ' is ')
			if n.connected:
				f.write('up\n')
			else:
				f.write('down\n')
			f.write('==================================\n')
		# report the outages
		print 'queue size = ', queue.qsize()
		while queue.empty() == False:
			print '>>'
			outage = queue.get()
			f.write(str(outage.getIp()) + ' was out at ' + time.strftime('%X', time.localtime(outage.getDown())) + ' until ' + time.strftime('%X', time.localtime(outage.getUp())) + '\n')
		f.close()

# test function to load queue for report
def load_queue(queue, nodes):
	lastHr = 0
	lastMin = 0
	i = 0
	j = 0
	for n in nodes:
		# need to adjust for test day/date
		for k in xrange(1,5):
			t1 = time.mktime([2015, 12, 21, lastHr + i, lastMin + j, 0, 0, 355, 1])
			i += 1
			j += 3
			t2 = time.mktime([2015, 12, 21, lastHr + i, lastMin + j, 0, 0, 355, 1])
			i += 2
			j += 5
			queue.put(Outage(n.getIp(), t1, t2))
			print 'outage queue size = ', queue.qsize()

if __name__ == '__main__':
	nodes = load_nodes('nodes.txt')
	load_queue(outages, nodes)
	print 'outage queue size = ', outages.qsize()
	write_report(outages, nodes)
	# one thread per node to ping and generate outage items
	# one thread to collect outages every 24 hours and generate a report to be emailed
	# one thread to run every 24 hours (or while there are reports to be mailed) to mail reports

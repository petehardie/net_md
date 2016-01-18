#!/usr/bin/env python

# ping.py
#
# issues:
# how to handle an outage that never comes back?
# 	report status at the 24 hr mark for each node
#

import sys
import subprocess
import datetime
import time
import Queue
import logging
import threading
import ConfigParser

# TODO use a dict for config values used
# test mode flag
testMode = True

# ping timeout for connected and when failing, real and test run values
real_timeout = { True : 60, False : 5 } # timeout for when up, and when down
test_timeout = { True : 15, False : 5 } # timeout for when up, and when down
timeout = test_timeout;

# report interval, real and test run values
real_reportTimeout = 24 * 60 * 60
test_reportTimeout = 5 * 60
reportTimeout = test_reportTimeout

outages = Queue.Queue() # the queue of outage reports

# where the reports file be written
# default, could be set in config read, but ok here
test_reportDir = "./reports"
reportDir = test_reportDir

# file with nodes to ping
# default, could be set in config read, but ok here
nodefile = 'nodes.txt'

class Outage:
	def __init__(self, ip, down, up):
		self.ip = ip # IP address
		self.down = down # time connection went down
		self.up = up # time connection was restored
		logging.debug("recorded an outage for IP " + str(ip))

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
		self.failCount = 0
		logging.debug("Created node for IP:" + str(self.address))

	def getAddress(self):
		return self.address

	# need to track 2+ failures as outage, and try 2 second timeouts on the ping
	def ping(self):
		try:
			logging.debug("pinging " + str(self.address))
			# -W2 for ping?
			#ping_response = subprocess.check_call(["/bin/ping", "-c1", "-w2", self.address], stdout=subprocess.PIPE)
			ping_response = subprocess.check_call(["/bin/ping", "-c1", "-W2", self.address], stdout=subprocess.PIPE)
			if self.connected == False:
				logging.debug("node " + str(self.address) + " back online")
				self.connected = True
				# record the outage
				self.outages.put(Outage(self.address, self.downAt, time.time()))
			self.failCount = 0
		except:
			if self.connected == True:
				self.failCount += 1
				logging.debug("ip " + str(self.address) + " failed count " + str(self.failCount));
				if self.failCount > 2:
					self.connected = False
					logging.debug("ip " + self.address + " considered down ");
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
# TODO modify to spawn a thread to write the report, so that write/dir errors do not stop system
reportCount = 0
def report(queue, nodes):
	while True:
		time.sleep(reportTimeout) # sleep 24 hours
		threading.Thread(target=write_report, args=(queue, nodes,)).start()
		#write_report(queue, nodes)

def write_report(queue, nodes):
		# generate filename from date
		logging.debug("creating a report")
		d = datetime.date.today()
		global reportCount
		#filename = str(d.year) + str(d.month) + str(d.day)
		filename = str(d.year) + str(d.month) + str(d.day) + '_' + str(reportCount)
		reportCount += 1
		path = reportDir + '/' + filename
		f = open(path, 'w')
		# report on the node status
		for n in nodes:
			f.write('Node ' + n.getAddress() + ' is ')
			if n.connected:
				f.write('up\n')
			else:
				f.write('down\n')
			f.write('==================================\n')
		# report the outages
		#print 'queue size = ', queue.qsize()
		while queue.empty() == False:
			#print '>>'
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
			#print 'outage queue size = ', queue.qsize()

# TODO pass in dict for config values in use
def readConfig():
	config = ConfigParser.ConfigParser()
	config.read("ping.config")
	global testMode
	global timeout
	global reportTimeout
	global ndoefile
	global reportDir
	for s in config.sections():
		for o in config.options(s):
			value = config.get(s, o)
			print o, value
			if o == 'test':
				if value == 'True':
					testMode = True
				else:
					testMode = False
			if o == 'nodefile':
				nodefile = value
			if o == 'reportdir':
				reportDir = value
	if testMode:
		timeout = test_timeout
		reportTimeout = test_reportTimeout
	else:
		timeout = real_timeout
		reportTimeout = real_reportTimeout
	# TODO change to logging, probably ERROR so they are always visible
	print 'testMode = ', testMode
	print 'timeout = ', timeout
	print 'nodefile = ', nodefile
	print 'reportDir = ', reportDir
	print 'reportTimeout = ', reportTimeout
	#sys.exit()

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(asctime)s %(message)s',)
#logging.basicConfig(level=logging.ERROR, format='[%(levelname)s] %(asctime)s %(message)s',)

if __name__ == '__main__':
	# read config file
	readConfig()
	# need to read this file from config
	nodes = load_nodes(nodefile)

	# test the report
	#load_queue(outages, nodes)
	##print 'outage queue size = ', outages.qsize()
	#write_report(outages, nodes)

	# test the emailer TBD -- replaced with putting report files under dropbox folder for sync
	# one thread to run every 24 hours (or while there are reports to be mailed) to mail reports

	# one thread per node to ping and generate outage items - call monitor()
	# one thread to collect outages every 24 hours and generate a report to be emailed - call report()

	# TODO need to change to have something monitor ping threads and respawn if needed
	# use isAlive() on the threads
	# ? how to monitor ?
	# 
	# TODO use daemon threads to make exit cleaner?
	node_threads = []
	for n in nodes:
		t = threading.Thread(target=monitor, args=(n,))
		node_threads.append(t)
		t.start()
	report_thread = threading.Thread(name="REPORT", target=report, args=(outages, nodes,))
	report_thread.start()

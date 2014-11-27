# This script helps you to detect your new table and add it to your slony setting
# You can use this script as cronjob, however this script is need to be tested more
# Author: bagus.trihatmaja@gmail.com
# Version 2.1

import psycopg2
import subprocess
import sys
import os
import threading
import time
import numpy as np


## Change this based on your config
SLON_PATH 		= os.environ.get('SLON_PATH')
SLONIK_PATH		= os.environ.get('SLONIK_PATH')
CLUSTERNAME		= os.environ.get('CLUSTERNAME')
MASTERDBNAME	= os.environ.get('MASTERDBNAME')
SLAVEDBNAME		= os.environ.get('SLAVEDBNAME')
MASTERHOST 		= os.environ.get('MASTERHOST')
SLAVEHOST 		= os.environ.get('SLAVEHOST')
REPLICATIONUSER = os.environ.get('REPLICATIONUSER')
REPLICATIONPASSWORD = os.environ.get('REPLICATIONPASSWORD')
SCHEMANAME = os.environ.get('SCHEMANAME')
ADDTABLEFILENAME = os.environ.get('ADDTABLEFILENAME','command_add_table')
ADDSEQUENCEFILENAME = os.environ.get('ADDSEQUENCEFILENAME','command_add_sequence')

if (SLON_PATH or SLONIK_PATH or CLUSTERNAME or \
 MASTERDBNAME or SLAVEDBNAME or MASTERHOST or \
 SLAVEHOST  or REPLICATIONUSER or REPLICATIONPASSWORD or SCHEMANAME) is None :
	print "Please set the environment variables first"
	sys.exit()

if os.path.exists("add_table.pid"):
	print "This script is already running. If it is not running try to remove add_table.pid and run it again."
	sys.exit()
else:
	try:
		f = open("add_table.pid",'w')
		f.write(str(os.getpid()))
		f.close()
	except Exception, e:
		raise e
		os.remove("add_table.pid")
	

## Database init
try:
	conn_master = psycopg2.connect("dbname='{MASTERDBNAME}' user='{REPLICATIONUSER}' host='{MASTERHOST}' password='{REPLICATIONPASSWORD}'".format( \
		MASTERDBNAME=MASTERDBNAME, \
		REPLICATIONUSER=REPLICATIONUSER, \
		MASTERHOST=MASTERHOST, \
		REPLICATIONPASSWORD=REPLICATIONPASSWORD))
	conn_slave = psycopg2.connect("dbname='{SLAVEDBNAME}' user='{REPLICATIONUSER}' host='{SLAVEHOST}' password='{REPLICATIONPASSWORD}'".format( \
		SLAVEDBNAME=SLAVEDBNAME, \
		REPLICATIONUSER=REPLICATIONUSER, \
		SLAVEHOST=SLAVEHOST, \
		REPLICATIONPASSWORD=REPLICATIONPASSWORD))
except Exception, e:
  print "unable to connect"
  sys.exit()

cur_master = conn_master.cursor()
cur_slave = conn_slave.cursor()

## Threading arrays
threadsTable = []
threadsSequence = []

class TableThread(threading.Thread):
	def __init__(self, counter, table):
		threading.Thread.__init__(self)
		self.table = table
		self.counter = counter
	def run(self):
		doProcessForTable(self.counter, self.table)
		

class SequenceThread(threading.Thread):
	def __init__(self, counter, sequence):
		threading.Thread.__init__(self)
		self.sequence = sequence
		self.counter = counter
	def run(self):
		doProcessForSequence(self.counter, self.sequence)
	

## ALL FUNCTIONS BELOW:

## Each ID in slony is unique. There are many ID in slony schema, but for now we only need
## some of them. They are: set_id, tab_id, seq_id, and sub_set
## So, if we want to add something first we need to know the latest ID + 1

def getLatestSetID():
	## New set id
	cur_master.execute("select max(set_id) + 1 as set_id from _{CLUSTERNAME}.sl_set".format(CLUSTERNAME=CLUSTERNAME))
	return cur_master.fetchone()

def getLatestTableID():
	## New table id
	cur_master.execute("select max(tab_id) + 1 as tab_id from _{CLUSTERNAME}.sl_table".format(CLUSTERNAME=CLUSTERNAME))
	return cur_master.fetchone()

def getLatestSequenceID():
	## NEW SEQUENCE ID
	cur_master.execute("select max(seq_id) + 1 as seq_id from _{CLUSTERNAME}.sl_sequence".format(CLUSTERNAME=CLUSTERNAME))
	return cur_master.fetchone()

def getLatestSubscribeID():
	## NEW SUBSCRIBE ID
	cur_master.execute("select max(sub_set) + 1 as sub_set from _{CLUSTERNAME}.sl_subscribe".format(CLUSTERNAME=CLUSTERNAME))
	return cur_master.fetchone()

def getTableDiff(query):
	cur_master.execute(query)
	cur_slave.execute(query)
	master_table = cur_master.fetchall()
	slave_table = cur_slave.fetchall()
	return set(master_table).symmetric_difference(set(slave_table))

def getSequenceDiff(query, query_schema):
	cur_master.execute(query)
	cur_slave.execute(query_schema)
	master_sequence = cur_master.fetchall()
	slave_sequence = cur_slave.fetchall()
	return set(master_sequence).symmetric_difference(set(slave_sequence))

def dumpSchema(table):
	## Dump the schema of the new table
	pg_dump = subprocess.Popen(('pg_dump', '-U', 'postgres', '-s', MASTERDBNAME, '-t', table[0]), stdout=subprocess.PIPE)
	psql = subprocess.Popen(('psql', '-U', 'postgres', '-h', SLAVEHOST, SLAVEDBNAME), stdin=pg_dump.stdout, stdout=subprocess.PIPE)
	pg_dump.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
	output = psql.communicate()[0]

## Create new sequence command
def createAddSequenceFile(i, sequence):
	## Create slonik command file
	COMMAND_TEMPLATE = """
	
	#--
	# define the namespace the replication system uses in our example it is
	# slony_example
	#--

	cluster name = {CLUSTERNAME};

	#--
	# admin conninfo's are used by slonik to connect to the nodes one for each
	# node on each side of the cluster, the syntax is that of PQconnectdb in
	# the C-API
	# --
	node 1 admin conninfo = 'dbname={MASTERDBNAME} host={MASTERHOST} user={REPLICATIONUSER} password={REPLICATIONPASSWORD}';
	node 2 admin conninfo = 'dbname={SLAVEDBNAME} host={SLAVEHOST} user={REPLICATIONUSER} password={REPLICATIONPASSWORD}';
	create set (id={new_set_id}, origin=1, comment='a second replication set');
	set add sequence (set id={new_set_id}, origin=1, id={new_seq_id}, fully qualified name = '{SCHEMANAME}.{new_sequence_name}', comment ='some new sequence');
	subscribe set(id={new_sub_id}, provider=1,receiver=2);
	merge set(id=1, add id={new_sub_id},origin=1);
	""".format(CLUSTERNAME=CLUSTERNAME, \
		MASTERDBNAME=MASTERDBNAME, \
		MASTERHOST=MASTERHOST, \
		SLAVEDBNAME=SLAVEDBNAME, \
		SLAVEHOST=SLAVEHOST, \
		REPLICATIONUSER=REPLICATIONUSER, \
		REPLICATIONPASSWORD=REPLICATIONPASSWORD, \
		SCHEMANAME=SCHEMANAME, \
		new_set_id=NEW_SET_ID[0] + i, \
		new_seq_id=NEW_SEQ_ID[0] + i, \
		new_sequence_name=sequence[0], \
		new_sub_id= NEW_SUB_ID[0] + i)
	## Create file of the command table 
	f = open(ADDSEQUENCEFILENAME + str(i),'w')
	f.write(COMMAND_TEMPLATE)
	f.close()

## Create new table command
def createAddTableFile(i, table):
	## Create slonik command file
	COMMAND_TEMPLATE = """
	
	#--
	# define the namespace the replication system uses in our example it is
	# slony_example
	#--

	cluster name = {CLUSTERNAME};

	#--
	# admin conninfo's are used by slonik to connect to the nodes one for each
	# node on each side of the cluster, the syntax is that of PQconnectdb in
	# the C-API
	# --
	node 1 admin conninfo = 'dbname={MASTERDBNAME} host={MASTERHOST} user={REPLICATIONUSER} password={REPLICATIONPASSWORD}';
	node 2 admin conninfo = 'dbname={SLAVEDBNAME} host={SLAVEHOST} user={REPLICATIONUSER} password={REPLICATIONPASSWORD}';
	create set (id={new_set_id}, origin=1, comment='a second replication set');
	set add table (set id={new_set_id}, origin=1, id={new_tab_id}, fully qualified name = '{SCHEMANAME}.{new_table_name}', comment ='some new table');
	subscribe set(id={new_sub_id}, provider=1,receiver=2);
	merge set(id=1, add id={new_sub_id},origin=1);
	""".format(CLUSTERNAME=CLUSTERNAME, \
		MASTERDBNAME=MASTERDBNAME, \
		MASTERHOST=MASTERHOST, \
		SLAVEDBNAME=SLAVEDBNAME, \
		SLAVEHOST=SLAVEHOST, \
		REPLICATIONUSER=REPLICATIONUSER, \
		REPLICATIONPASSWORD=REPLICATIONPASSWORD, \
		SCHEMANAME=SCHEMANAME, \
		new_set_id=NEW_SET_ID[0] + i, \
		new_tab_id=NEW_TAB_ID[0] + i, \
		new_table_name=table[0], \
		new_sub_id= NEW_SUB_ID[0] + i)
	## Create file of the command table 
	f = open(ADDTABLEFILENAME + str(i),'w')
	f.write(COMMAND_TEMPLATE)
	f.close()

def callSlonik(file_name):
	## Now execute slonik
	slonik = ['slonik', file_name]
	subprocess.call(slonik)

def doProcessForTable(i, table):
	print "Execute {table}\n".format(table=table[0])
	dumpSchema(table)
	createAddTableFile(i, table)
	callSlonik(ADDTABLEFILENAME + str(i))
	os.remove(ADDTABLEFILENAME + str(i))

def doProcessForSequence(i, sequence):
	print "Execute {sequence}\n".format(sequence=sequence[0])
	createAddSequenceFile(i, sequence)
	callSlonik(ADDSEQUENCEFILENAME + str(i))
	os.remove(ADDSEQUENCEFILENAME + str(i))

if __name__ == "__main__":
	## Get the latest ID needed
	NEW_SET_ID = getLatestSetID()
	NEW_TAB_ID = getLatestTableID()
	NEW_SUB_ID = getLatestSubscribeID()
	NEW_SEQ_ID = getLatestSequenceID()

	## find the difference of the table
	query = "select table_name from information_schema.tables where table_schema='{SCHEMANAME}'".format(SCHEMANAME=SCHEMANAME)
	not_replicated_table = getTableDiff(query)


	## Add every new table to the set
	i = 0
	for table in not_replicated_table:
		threadTable = TableThread(i, table)
		threadTable.start()
		threadsTable.append(threadTable)
		## Adding so many tables at once leads to "too many clients already"
		## If this condition happens, subscription process will be stuck
		## So I will limit the threads to 10 threads and sleep for 10 secs
		## It will be faster and give a cooling down for the threads to complete
		if i % 10 == 0:
			time.sleep(10)
		i += 1

	for t in threadsTable:
		t.join()

	## Get new ID again
	NEW_SET_ID = getLatestSetID()
	NEW_TAB_ID = getLatestTableID()
	NEW_SUB_ID = getLatestSubscribeID()
	NEW_SEQ_ID = getLatestSequenceID()

	# ## find the difference of the sequence
	query = "select sequence_name from information_schema.sequences where sequence_schema='{SCHEMANAME}'".format(SCHEMANAME=SCHEMANAME)
	query_schema = "select seq_relname from _myrep.sl_sequence where seq_nspname='{SCHEMANAME}'".format(SCHEMANAME=SCHEMANAME)
	not_replicated_sequence = getSequenceDiff(query, query_schema)

	## Add every new sequence to the set
	i = 0
	for sequence in not_replicated_sequence:
		threadSequence = SequenceThread(i, sequence)
		threadSequence.start()
		threadsSequence.append(threadSequence)
		## Adding so many tables at once leads to "too many clients already"
		## If this condition happens, subscription process will be stuck
		## So I will limit the threads to 10 threads and sleep for 10 secs
		## It will be faster and give a cooling down for the threads to complete
		if i % 10 == 0:
			time.sleep(10)
		i += 1

	for t in threadsSequence:
		t.join()

	print "Exiting ..."


	cur_master.close()
	cur_slave.close()
	conn_master.close()
	conn_slave.close()
	os.remove("add_table.pid")



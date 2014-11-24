# This script helps you to detect your new table and add it to your slony setting
# You can use this script as cronjob, however this script is need to be tested more
# Author: bagus.trihatmaja@gmail.com

import psycopg2
import subprocess
import sys
import os
import numpy as np


## Change this based on your config
SLON_PATH 		= '/Library/PostgreSQL/9.3/bin'
SLONIK_PATH		= '/Library/PostgreSQL/9.3/bin/bin/slonik'
CLUSTERNAME		= 'myrep'
MASTERDBNAME	= 'master'
SLAVEDBNAME		= 'slave'
MASTERHOST 		= 'localhost'
SLAVEHOST 		= 'localhost'
REPLICATIONUSER = 'postgres'
REPLICATIONPASSWORD = 'postgres'
SCHEMANAME = 'public'
ADDTABLEFILENAME = 'command_add_table'
ADDSEQUENCEFILENAME = 'command_add_sequence'


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

def getSequenceDiff(query):
	cur_master.execute(query)
	cur_slave.execute(query)
	master_sequence = cur_master.fetchall()
	slave_sequence = cur_slave.fetchall()
	return set(master_sequence).symmetric_difference(set(slave_sequence))

def dumpSchema():
	## Dump the schema of the new table
	pg_dump = subprocess.Popen(('pg_dump', '-U', 'postgres', '-s', MASTERDBNAME, '-t', table[0]), stdout=subprocess.PIPE)
	psql = subprocess.Popen(('psql', '-U', 'postgres', '-h', SLAVEHOST, SLAVEDBNAME), stdin=pg_dump.stdout, stdout=subprocess.PIPE)
	pg_dump.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
	output = psql.communicate()[0]

def createAddTableFile():
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
	print COMMAND_TEMPLATE
	## Create file of the command table 
	f = open(ADDTABLEFILENAME,'w')
	f.write(COMMAND_TEMPLATE)
	f.close()

def callSlonik(file_name):
	## Now execute slonik
	slonik = ['slonik', file_name]
	subprocess.call(slonik)


if __name__ == "__main__":
	## Get the latest ID needed
	NEW_SET_ID = getLatestSetID()
	NEW_TAB_ID = getLatestTableID()
	NEW_SUB_ID = getLatestSubscribeID()
	NEW_SEQ_ID = getLatestSequenceID()

	## find the difference of the table
	query = "select table_name from information_schema.tables where table_schema='{SCHEMANAME}'".format(SCHEMANAME=SCHEMANAME)
	not_replicated_table = getTableDiff(query)

	## find the difference of the sequence
	query = "select sequence_name from information_schema.sequences where sequence_schema='{SCHEMANAME}'".format(SCHEMANAME=SCHEMANAME)
	not_replicated_sequence = getSequenceDiff(query)

	## Add every new table to the set
	i = 0
	for table in not_replicated_table:
		dumpSchema()
		createAddTableFile()
		callSlonik(ADDTABLEFILENAME)
		i += 1



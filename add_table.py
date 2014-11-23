import psycopg2
import subprocess
import sys
import os
import numpy as np



SLON_PATH 		= '/Library/PostgreSQL/9.3/bin'
SLONIK_PATH		= '/Library/PostgreSQL/9.3/bin/bin/slonik'
CLUSTERNAME		= 'myrep'
MASTERBDBNAME	= 'master'
SLAVEDBNAME		= 'slave'
MASTERHOST 		= 'localhost'
SLAVEHOST 		= 'localhost'
REPLICATIONUSER = 'postgres'
REPLICATIONPASSWORD = 'postgres'

if __name__ == "__main__":
	
	try:
	  conn_master = psycopg2.connect("dbname='master' user='postgres' host='localhost' password='postgres'")
	  conn_slave = psycopg2.connect("dbname='slave' user='postgres' host='localhost' password='postgres'")
	except Exception, e:
	  print "unable to connect"
	  sys.exit()

	cur_master = conn_master.cursor()
	cur_slave = conn_slave.cursor()

	## NEW SET ID
	cur_master.execute("select max(set_id) + 1 as set_id from _myrep.sl_set")
	new_set_id = cur_master.fetchone()

	## NEW TABLE ID
	cur_master.execute("select max(tab_id) + 1 as tab_id from _myrep.sl_table")
	new_tab_id = cur_master.fetchone()

	## NEW SEQUENCE ID
	cur_master.execute("select max(seq_id) + 1 as tab_id from _myrep.sl_sequence")
	new_seq_id = cur_master.fetchone()

	## NEW SUBSCRIBE ID
	cur_master.execute("select max(sub_set) + 1 as sub_set from _myrep.sl_subscribe ;")
	new_sub_id = cur_master.fetchone()
	

	## find the difference of the table
	cur_master.execute("select table_name from information_schema.tables where table_schema='public'")
	cur_slave.execute("select table_name from information_schema.tables where table_schema='public'")
	master_table = cur_master.fetchall()
	slave_table = cur_slave.fetchall()
	not_replicated_table = set(master_table).symmetric_difference(set(slave_table))


	## find the difference of the sequence
	cur_master.execute("select sequence_name from information_schema.sequences where sequence_schema='public'")
	cur_slave.execute("select sequence_name from information_schema.sequences where sequence_schema='public'")
	master_sequence = cur_master.fetchall()
	slave_sequence = cur_slave.fetchall()
	not_replicated_sequence = set(master_sequence).symmetric_difference(set(slave_sequence))

	i = 0
	for table in not_replicated_table:
		pg_dump = subprocess.Popen(('pg_dump', '-U', 'postgres', '-s', 'master', '-t', table[0]), stdout=subprocess.PIPE)
		psql = subprocess.Popen(('psql', '-U', 'postgres', '-h', 'localhost', 'slave'), stdin=pg_dump.stdout, stdout=subprocess.PIPE)
		pg_dump.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
		output = psql.communicate()[0]

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
		set add table (set id={new_set_id}, origin=1, id={new_tab_id}, fully qualified name = 'public.{new_table_name}', comment ='some new table');
		subscribe set(id={new_sub_id}, provider=1,receiver=2);
		merge set(id=1, add id={new_sub_id},origin=1);
		""".format(CLUSTERNAME=CLUSTERNAME, \
			MASTERDBNAME=MASTERBDBNAME, \
			MASTERHOST=MASTERHOST, \
			SLAVEDBNAME=SLAVEDBNAME, \
			SLAVEHOST=SLAVEHOST, \
			REPLICATIONUSER=REPLICATIONUSER, \
			REPLICATIONPASSWORD=REPLICATIONPASSWORD, \
			new_set_id=new_set_id[0] + i, \
			new_tab_id=new_tab_id[0] + i, \
			new_table_name=table[0], \
			new_sub_id= new_sub_id[0] + i)
		print COMMAND_TEMPLATE
		f = open('myfile','w')
		f.write(COMMAND_TEMPLATE)
		f.close()
		slonik = ['slonik', 'myfile']
		subprocess.call(slonik)
		i += 1




	



	
	

	


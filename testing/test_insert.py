import time
import psycopg2
import os
import sys

if __name__ == "__main__":
	try:
	  conn = psycopg2.connect("dbname='master' user='postgres' host='localhost' password='postgres'")
	except Exception, e:
	  print "unable to connect"
	  sys.exit()

	cur = conn.cursor()
	for x in xrange(1,10):
		print x
		cur.execute("INSERT INTO reptable5 VALUES(%s)", (x,))
		#cur.execute("SELECT * FROM reptable5")
		#cur.fetchone()
		time.sleep(1)

	conn.commit()
	cur.close()
	conn.close()
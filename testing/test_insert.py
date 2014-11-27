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
	for x in xrange(1,1000):
		print x
		cur.execute("INSERT INTO reptable166 (name) VALUES(%s)", ("test" + str(x),))
		conn.commit()
		time.sleep(1)

	cur.close()
	conn.close()
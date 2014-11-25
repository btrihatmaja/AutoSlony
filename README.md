AutoSlony
=========

Automatically detect your new table and add it to your Slony set!

Note: For now, this script only support for table adding and one master to one slave replication.

Why?
---------
Schema changes in Slony requires another configuration. So the purpose of this script is to make Slony replication works like [Streaming Replication](https://wiki.postgresql.org/wiki/Streaming_Replication).

Requirement
----------
1. Python >= 2.6
2. Psycopg2
3. Numpy

How this works & How to use
---------
This script will look for your `information_schema.tables` table in both your master and your slave and compare both of them. If there is tables missing in your slave then this script will add those tables to your slave and reconfigure slony automatically. 

Normally, you just need to create the table in your master server only and run `python add_table.py`. It will detect your new table and add it to your slave, so you don't need to use `execute script` slony's command or create table in your slave manually.
You can run this script by using `crontab` as well, so your table will be automatically copied to your slave. But if you use crontab, make sure your slony user does not require password to connect to your database.

Test
-------
The `testing` folder contains the test I've done, using postgreSQL 9.3.5 and slonyI 2.3.3.

Slony config
-------
I also provide initial slony config in my `slony_config` folder. However this config will work only in SlonyI >= 2.1. To see a full documentation about how to install Slony please refer to [this document](http://slony.info/documentation/)

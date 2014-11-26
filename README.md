AutoSlony
=========

Automatically detect your new table and add it to your Slony set!

Note: For now, this script only support for table and sequence adding and one master to one slave replication.

Why?
---------
Schema changes in Slony requires another configuration. So the purpose of this script is to make Slony replication works like [Streaming Replication](https://wiki.postgresql.org/wiki/Streaming_Replication).

Requirement
----------
1. Python >= 2.6
2. Psycopg2
3. Numpy

```bash
# For Ubuntu 
sudo apt-get install python python-dev python-pip

pip install psycopg2
pip install numpy
```

How this works & How to use
---------
This script will look for your `information_schema.tables` table in both your master and your slave and compare both of them. If there is tables missing in your slave then this script will add those tables to your slave and reconfigure slony automatically. 

Normally, you just need to create the table in your master server only and run `python add_table.py`. It will detect your new table and add it to your slave, so you don't need to use `execute script` slony's command or create table in your slave manually.
You can run this script by using `crontab` as well, so your table will be automatically copied to your slave. But if you use crontab, make sure your slony user does not require password to connect to your database.

There are few configuration before you start to run this script. This configuration is inside `slony_config/set_env`, you can open it using your favorite text editor.

Example:

```bash
SLON_PATH=/Library/PostgreSQL/9.3/bin/ 
SLONIK_PATH=/Library/PostgreSQL/9.3/bin/bin
CLUSTERNAME=myrep
MASTERDBNAME=master
SLAVEDBNAME=slave
MASTERHOST=localhost
SLAVEHOST=localhost
REPLICATIONUSER=postgres
REPLICATIONPASSWORD=postgres 
SCHEMANAME=public
ADDTABLEFILENAME=add_table_file
ADDSEQUENCEFILENAME =add_sequence_file
```

And run:

```bash
cat /slony_config/set_env >> .bash_profile
source ~/.bash_profile
```

To run the script

```bash
#After adding the table to your master
python add_table.sh
```

Test
-------
The `testing` folder contains the test I've done, using postgreSQL 9.3.5 and slonyI 2.3.3.

Slony config
-------
I also provide initial slony config in my `slony_config` folder. However this config will work only in SlonyI >= 2.1. Please read the full documentation about how to install Slony in [this document](http://slony.info/documentation/).

How to do initial config (_Remember to set your environtment variable first using set_env.sh_):

```bash
## In your master
./slony_config/slonny_config | slonik 

## In your master
slon myrep "dbname=master user=postgres password=postgres host=localhost" > /dev/null 2>&1

## In your slave
slon myrep "dbname=slave user=postgres password=postgres host=localhost" > /dev/null 2>&1

## In your master 
./slony_config/subscribe | slonik 
```

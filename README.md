# mqtt-to-sql

Julien Aube - 2020

This python script subscribes to MQTT broker topic prefix given as a config file
and inserts the topic into a PostgreSQL database table.
The database name is the first word of the topic, usually in uppercase.

## Installation
### Prerequisite
* Python 3
* Paho MQTT , configparse and PsycoPG2

To install it (Debian 10) to you python environment use
```
sudo apt-get install python3-paho-mqtt python3-configargparse python3-psycopg2
```

The config file shall be filled with adequat values and then installed in /etc/default/mqtt-to-sql.
mqtt-to-sql.py shall be copied to /usr/local/bin.
mqtt-to-sql.service shall be copied to /etc/systemd/system/

### SQL database init
Create database tables to Postgresql using the following SQL command
Using the "create_hypertable()" statement is optional , it is used only when Postgresql is used
with the TimescaleDB extension.

The script does not uses TimescaleDB at all for SELECT or UPDATE, but this extension changes how the
table are stored to disk for better performances when used in a time-serie database .
```
CREATE TABLE sensorref (
        sensorid SERIAL,
        location TEXT   NOT NULL,
        type     TEXT   NOT NULL,
        ref      TEXT   NOT NULL,
        unit     TEXT   NOT NULL,
        PRIMARY KEY(sensorid)
);

CREATE TABLE metrics (
	time		TIMESTAMPTZ	NOT NULL,
	sensorid 	INTEGER REFERENCES sensorref(sensorid),
	value		DOUBLE PRECISION NOT NULL,
        PRIMARY KEY(time, sensorid)
);
SELECT create_hypertable('metrics', 'time');

CREATE TABLE infos (
        time            TIMESTAMPTZ     NOT NULL,
	sensorid        INTEGER REFERENCES sensorref(sensorid),
	value           TEXT NOT NULL,
	PRIMARY KEY(time, sensorid)
);
SELECT create_hypertable('infos', 'time');
```
## Usage

The script subscribes to the MQTT topic header specified in the config file.
This topic shall also be the name of the database.

Then, each message received splits the topic in words (described in the file MQTT_Naming_Rules.txt). 
These words together defines a "sensor" , which is added to a sensorref table with a unique "sensorid". This may be used for labeling graphs, ...
The values are then updated to the database table (specified in the first word of the topic, currently "metrics") with a timestamp.
There is a cache , so value that do not change are not updated to the database. 

#!/usr/bin/env python3

import time
import configparser
import paho.mqtt.client as mqttClient
import psycopg2

def update_sensorID(userData,topic):
    sql_request = "SELECT sensorid FROM sensorref WHERE location = %s "+\
                  "AND type = %s AND ref = %s;"
    userData.psqlcursor.execute(sql_request, (topic[2],topic[3],topic[4]))
    row = userData.psqlcursor.fetchone()
    if row is None:
       # This is a new sensor, add it to the SensorRefs table
       sql_request = "INSERT INTO sensorref (location,type,ref,unit) "+\
                     "VALUES (%s,%s,%s,%s) RETURNING sensorid;"
       userData.psqlcursor.execute(sql_request, (topic[2], topic[3], topic[4], topic[5]))
       row = userData.psqlcursor.fetchone()
    return row[0]

def update_value(userData,table,sensorID,payload):
    sql_request = "INSERT INTO " + table + " (time,sensorid,value) VALUES (NOW(),%s,%s);"
    userData.psqlcursor.execute(sql_request, (sensorID,payload))
    print("MQTT to SQL : Updated to DB")


def check_last_value(userdata,table,sensorID,payload):
    if (userData.sensorvals.get(sensorID) == payload):
        return False
    else:
        sql_request = "SELECT value FROM " + table + " WHERE sensorid = %s ORDER BY time LIMIT 1;"
        userData.psqlcursor.execute(sql_request, (sensorID,))
        row = userData.psqlcursor.fetchone()
        if (row is not None) and (row[0] == payload):
           userData.sensorvals[sensorID] = payload
           return False
        return True

def on_mqtt_message(client, userData, msg):
    # Check if the database is the good one and exit if not
    topic = msg.topic.split('/')
    if topic[0] != config["MQTT"]["topic"]:
        return

    # Check for sensorID. First look in cache, then in database, finally create it
    # if required and cache it in userData.sensorefs
    if msg.topic in userData.sensorref:
        sensorID = userData.sensorref[msg.topic]
        print(F"MQTT to SQL : Received message for cached sensorid={sensorID},",end='')
    else:
        sensorID = update_sensorID(userData,topic)
        userData.sensorref[msg.topic] = sensorID
        print(F"MQTT to SQL : Received message for new sensorid={sensorID},",end='')


    if (topic[5] == "text"):
        table = "Infos"
        payload = msg.payload.decode()
    elif (topic[5] == "int"):
        table = "Metrics"
        payload = int(msg.payload)
    else:
        table = "Metrics"
        payload = float(msg.payload)

    print(F" value={payload}")


    if ( check_last_value(userData,table,sensorID,payload)):
        update_value(userData,table,sensorID,payload)
        userData.sensorvals[sensorID] = payload

class userDataClass:
    """ Holds various data used within above callback """
    sensorref = dict()
    sensorvals = dict()
    psqlconn = None
    psqlcursor = None

userData = userDataClass()
config = configparser.ConfigParser()
config.read('/etc/default/mqtt-to-sql')
print("MQTT to SQL : Config file read OK")

###### MQTT Connexion #######
mqttclient = mqttClient.Client(client_id=config["MQTT"]["clientname"], clean_session=True,userdata=userData)
mqttclient.username_pw_set(config["MQTT"]["user"], password = config["MQTT"]["password"])
mqttclient.on_message=on_mqtt_message
mqttclient.connect(config["MQTT"]["broker"], port = int(config["MQTT"]["port"]))
mqttclient.subscribe(config["MQTT"]["topic"] + "/" + "#", 0)
time.sleep(0.1)
mqttclient.loop()
print("MQTT to SQL : MQTT broker connexion OK")

###### PostgreSQL Connexion #####
try:
    connect_str = "dbname='"   + config["MQTT"]["topic"]    + "'" +\
                  "user='"     + config["PSQL"]["user"]     + "'" +\
                  "host='"     + config["PSQL"]["host"]     + "'" +\
                  "password='" + config["PSQL"]["password"] + "'"

    userData.psqlconn = psycopg2.connect(connect_str)
    userData.psqlconn.set_session(autocommit=True)
    userData.psqlcursor = userData.psqlconn.cursor()

except psycopg2.Error as e:
    print(e)
    mqttclient.disconnect()

print("MQTT to SQL : Postgresql connexion OK")

##### Main loop ######
try:
    while True:
        mqttclient.loop()
        time.sleep(0.01)
except KeyboardInterrupt:
    mqttclient.disconnect()
    userData.psqlcursor.close()
    userData.psqlconn.close()


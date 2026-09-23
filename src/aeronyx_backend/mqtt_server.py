import os
import sys
import time
import json
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from src.aeronyx_backend.sensor_db import initialize_database, update_sensor_data, update_command_data

load_dotenv()
initialize_database()

MQTT_BROKER         = os.getenv("MQTT_BROKER")
MQTT_PORT           = int(os.getenv("MQTT_PORT"))
MQTT_USERNAME       = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD       = os.getenv("MQTT_PASSWORD")
MQTT_SENSOR_TOPIC   = os.getenv("MQTT_SENSOR_TOPIC")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"Subscribed: {mid} {granted_qos}")

def on_unsubscribe(client, userdata, mid):
    print(f"Unsubscribed: {mid}")

def on_publish(client, userdata, mid):
    print(f"Published: {mid}")

def on_message(client, userdata, msg):
    if msg.topic == MQTT_SENSOR_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Received sensor data: {payload}")
            update_sensor_data(payload)
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from sensor data: {msg.payload.decode()}")
    elif msg.topic == MQTT_COMMAND_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Received command: {payload}")
            update_command_data(payload)
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from command: {msg.payload.decode()}")
    else:
        print(f"Received message: {msg.topic} {msg.payload.decode()}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_SENSOR_TOPIC)
        print("MQTT server started and subscribed to topics:")
        print(f" - {MQTT_SENSOR_TOPIC}")
        print("------------------------------------------------\n\n")
    else:
        print(f"Failed to connect, return code {rc}")
        client.disconnect()

def on_disconnect(client, userdata, rc):
    client.unsubscribe(MQTT_SENSOR_TOPIC)
    print(f"Disconnected from MQTT Broker with return code {rc}")
    print("MQTT server stopped.")
    print("------------------------------------------------\n\n")

class MQTTServer:
    def __init__(self, host=None, port=None, username=None, password=None):
        self.host       = host or MQTT_BROKER
        self.port       = port or MQTT_PORT
        self.username   = username or MQTT_USERNAME
        self.password   = password or MQTT_PASSWORD

        print("--- HIVEMQ MQTT Server Initialization ---")
        print(f"Initializing MQTT server with host: {self.host}, port: {self.port}")
        print("------------------------------------------------\n\n")

        self.server                 = mqtt.Client()
        self.server.on_connect      = on_connect
        self.server.on_disconnect   = on_disconnect
        self.server.on_subscribe    = on_subscribe
        self.server.on_unsubscribe  = on_unsubscribe
        self.server.on_publish      = on_publish
        self.server.on_message      = on_message

        self.server.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS) 
        self.server.username_pw_set(self.username, self.password)
        

    async def start(self):
        # Start the MQTT server
        self.server.connect(self.host, self.port, 60)
        self.server.loop_start()
        

    async def stop(self):
        # Stop the MQTT server
        self.server.loop_stop()
        self.server.disconnect()
        

import paho.mqtt.client as mqtt

MQTT_SERVER = "broker.hivemq.com"
MQTT_PATH = "demo/opcua-sub-to-mqtt/server_test/variables/#"

def on_connect(client, userdata, flags, rc):
    print("[CONNECT]", rc)
    client.subscribe(MQTT_PATH, qos=1)

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"[SUBSCRIBED] mid:{mid} qos:{granted_qos}")

def on_message(client, userdata, msg):
    try:
        text = msg.payload.decode()
        print(f"[MESSAGE]\nTopic: {msg.topic}\n{text}\n{'-'*40}")
    except Exception as e:
        print(f"[DECODE_ERROR] {e} {msg.payload}")

def on_disconnect(client, userdata, rc):
    print("[DISCONNECT]", rc)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect

client.connect(MQTT_SERVER, 1883, 60)
client.loop_forever()

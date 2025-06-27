import asyncio
from asyncua import Client as OPCUAClient
from paho.mqtt import client as mqtt
import json

# OPC UA 설정
OPCUA_SERVER_URL = "opc.tcp://localhost:4840"
OPCUA_NODE_ID = "ns=2;i=2"

# MQTT 설정
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = f"demo/opcua-sub-to-mqtt/variables/{OPCUA_NODE_ID}"

# MQTT 콜백 함수 정의
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected with result code", rc)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    print(f"[MQTT] Received from topic {msg.topic}: {msg.payload.decode()}")

async def read_opcua_and_publish(mqtt_client):
    async with OPCUAClient(OPCUA_SERVER_URL) as client:
        print("[OPCUA] Connected to OPC UA Server.")
        node = client.get_node(OPCUA_NODE_ID)

        while True:
            val = await node.read_value()
            payload = {
                "value": val
            }
            mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
            print(f"[OPCUA->MQTT] Published: {val}")
            await asyncio.sleep(1)

async def main():
    # MQTT 클라이언트 설정 및 시작
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()

    # OPC UA 데이터 읽어서 MQTT로 보내기
    await read_opcua_and_publish(mqtt_client)

if __name__ == "__main__":
    asyncio.run(main())

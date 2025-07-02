import paho.mqtt.client as mqtt

# ====== 설정 ======
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "plc/device1/data"

# ====== 콜백 함수 정의 ======
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[CONNECTED] MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[SUBSCRIBED] Topic: {MQTT_TOPIC}")
    else:
        print(f"[FAILED] Connection error code: {rc}")

def on_message(client, userdata, msg):
    print(f"[RECEIVED] Topic: {msg.topic} | Payload: {msg.payload.decode('utf-8')}")

# ====== 클라이언트 생성 및 콜백 지정 ======
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"Trying to connect to Broker at {MQTT_BROKER}:{MQTT_PORT} ...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ====== 메시지 루프 시작 ======
client.loop_forever()

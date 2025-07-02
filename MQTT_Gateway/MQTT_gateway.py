# device1_mqtt_gateway.py

import asyncio
import json
import paho.mqtt.client as mqtt

from Device1_script import Device1Modbus   # device1_script.py 파일이 같은 폴더에 있다고 가정

# MQTT 브로커 설정
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "plc/device1/data"

async def mqtt_publish_task(device):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()  # MQTT loop in background

    try:
        while True:
            data = device.read_all()         # MODBUS 데이터 읽기
            payload = json.dumps(data)       # JSON 변환
            client.publish(MQTT_TOPIC, payload)   # MQTT 전송
            await asyncio.sleep(1)           # 1초마다 전송
    except asyncio.CancelledError:
        pass
    finally:
        client.loop_stop()
        client.disconnect()

async def main():
    device = Device1Modbus()
    # 데이터 시뮬레이션 비동기로 실행
    simulate_task = asyncio.create_task(device.simulate_data())
    # MQTT 전송 비동기로 실행
    publish_task = asyncio.create_task(mqtt_publish_task(device))

    await asyncio.gather(simulate_task, publish_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("종료됨")

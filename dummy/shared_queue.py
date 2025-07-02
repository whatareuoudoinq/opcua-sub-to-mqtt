# shared_queue.py
import asyncio

# MQTT 퍼블리셔와 GUI가 공유할 비동기 큐
send_queue = asyncio.Queue()

class MQTTStatusMessage:
    def __init__(self, status, broker, port, topics, detail=None):
        self.type = "mqtt_status"
        self.status = status
        self.broker = broker
        self.port = port
        self.topics = topics
        from datetime import datetime
        self.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.detail = detail
        
##########
# 사용 방법
# 데이터 넣기   : await send_queue.put(메시지)
# 데이터 꺼내기 : 메시지 = await send_queue.get()
##########
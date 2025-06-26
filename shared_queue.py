# shared_queue.py
import asyncio

# MQTT 퍼블리셔와 GUI가 공유할 비동기 큐
send_queue = asyncio.Queue()

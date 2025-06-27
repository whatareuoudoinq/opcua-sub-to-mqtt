# serial_handler.py
import asyncio
import serial_asyncio
from shared_queue import send_queue

# 포트 변경 등 명령을 위한 큐
serial_command_queue = asyncio.Queue()

class SerialMessage:
    def __init__(self, data, port):
        self.source = "serial"
        self.data = data
        self.port = port

async def serial_read_loop(port, baudrate):
    try:
        reader, writer = await serial_asyncio.open_serial_connection(url=port, baudrate=baudrate)
        print(f"[SerialHandler] Connected to {port} @ {baudrate}")
        while True:
            # 명령 큐 체크(포트 변경 등)
            try:
                cmd = serial_command_queue.get_nowait()
                if cmd["action"] == "change_port":
                    print(f"[SerialHandler] 포트 변경 명령 수신: {cmd['port']}, {cmd['baudrate']}")
                    writer.close()
                    await writer.wait_closed()
                    return  # 루프 재시작 유도
            except asyncio.QueueEmpty:
                pass

            data = await reader.readline()
            try:
                text = data.decode('utf-8').strip()
            except Exception:
                text = str(data)
            await send_queue.put(SerialMessage(text, port))
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"[SerialHandler] Serial error: {e}")
        await asyncio.sleep(2)

async def main(port="COM3", baudrate=115200):
    cur_port, cur_baud = port, baudrate
    while True:
        await serial_read_loop(cur_port, cur_baud)
        # 만약 포트 변경 명령이 있었으면 다음 루프에서 반영
        try:
            cmd = serial_command_queue.get_nowait()
            if cmd["action"] == "change_port":
                cur_port, cur_baud = cmd["port"], cmd["baudrate"]
        except asyncio.QueueEmpty:
            pass
        await asyncio.sleep(0.5)

# 포트 변경을 GUI 등에서 호출하는 함수
async def change_serial_port(port, baudrate):
    await serial_command_queue.put({"action": "change_port", "port": port, "baudrate": baudrate})

# __all__ 등록(명확성)
__all__ = ["main", "change_serial_port", "serial_command_queue"]

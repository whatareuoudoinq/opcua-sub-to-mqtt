# Device1_modbus.py
import asyncio

class Device1Modbus:
    def __init__(self):
        self.data = {
            40001: True,    # Status
            40002: 0,       # Tag1
        }
        self.running = True

    async def simulate_data(self):
        while self.running:
            self.data[40001] = True
            count = 0
            for _ in range(30):
                count += 1
                self.data[40002] = count
                await asyncio.sleep(1)
            self.data[40001] = False
            self.data[40002] = 0
            await asyncio.sleep(10)

    def read_all(self):
        return self.data.copy()

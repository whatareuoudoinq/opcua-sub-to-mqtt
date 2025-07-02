from asyncua import ua
import asyncio

CHANNEL_INFO = {
    "name": "Channel1",
    "driver": "Modbus TCP/IP Ethernet",
    "connection": "Ethernet"
}

class Device1:
    def __init__(self, device_node, idx):
        self.device_node = device_node
        self.idx = idx
        self.status_var = None
        self.tag1_var = None

    async def setup_vars(self):
        # 변수명 리스트 및 값/타입 정의
        tags = [
            {"name": "Status", "value": True, "vtype": ua.VariantType.Boolean},
            {"name": "Tag1", "value": 0, "vtype": ua.VariantType.Int32},
        ]
        for tag in tags:
            # NodeId 문자열을 자동으로 경로 생성
            nodeid_str = f"Channels/{CHANNEL_INFO['name']}/Device1/{tag['name']}"
            nodeid = ua.NodeId(nodeid_str, self.idx)
            var = await self.device_node.add_variable(
                nodeid, tag["name"], tag["value"], tag["vtype"]
            )
            setattr(self, f"{tag['name'].lower()}_var", var)

    async def run(self):
        while True:
            await self.status_var.write_value(ua.Variant(True, ua.VariantType.Boolean))
            count = 0
            for _ in range(30):
                count += 1
                await self.tag1_var.write_value(ua.Variant(count, ua.VariantType.Int32))
                await asyncio.sleep(1)
            await self.status_var.write_value(ua.Variant(False, ua.VariantType.Boolean))
            await self.tag1_var.write_value(ua.Variant(0, ua.VariantType.Int32))
            await asyncio.sleep(10)

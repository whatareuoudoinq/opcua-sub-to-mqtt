import asyncio
import logging
from asyncua import ua
from asyncua.server import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opcua-server")

CHANNEL = {
    "name": "Channel1",
    "driver": "Modbus TCP/IP Ethernet",
    "connection": "Ethernet"
}

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840")
    uri = "http://lee-eunseo-opcua.local"
    idx = await server.register_namespace(uri)

    # 채널/드라이버/커넥션 구조 (노드 트리)
    channels_obj = await server.nodes.objects.add_object(idx, "Channels")
    ch_node = await channels_obj.add_object(idx, CHANNEL["name"])
    driver_node = await ch_node.add_object(idx, "Driver")
    await driver_node.add_property(idx, "Type", CHANNEL["driver"])
    conn_node = await ch_node.add_object(idx, "Connection")
    await conn_node.add_property(idx, "Type", CHANNEL["connection"])

    # 장비 노드 및 변수 (스코프 밖에 선언)
    device_node = await ch_node.add_object(idx, "Device1")
    status_var = await device_node.add_variable(idx, "Status", True, ua.VariantType.Boolean)
    tag1_var = await device_node.add_variable(idx, "Tag1", 0, ua.VariantType.Int32)

    logger.info("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
    logger.info("[OPC UA Server] active! (channel=%s, driver=%s, connection=%s)",
                CHANNEL["name"], CHANNEL["driver"], CHANNEL["connection"])
    logger.info("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

    async with server:
        while True:
            # 장비 ON(30초)
            await status_var.write_value(ua.Variant(True, ua.VariantType.Boolean))
            count = 0
            for _ in range(30):
                count += 1
                await tag1_var.write_value(ua.Variant(count, ua.VariantType.Int32))
                await asyncio.sleep(1)
            # 장비 OFF(10초)
            await status_var.write_value(ua.Variant(False, ua.VariantType.Boolean))
            await tag1_var.write_value(ua.Variant(0, ua.VariantType.Int32))
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())

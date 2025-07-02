import asyncio
import logging
from asyncua import ua
from asyncua.server import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('opcua-server')

# 1. 채널/드라이버/커넥션(PLC와 연결)
CHANNELS = [{
    "name": "Channel1",
    "driver": "Modbus TCP/IP Ethernet",
    "connection": "Ethernet"
}]
# 실제로는 여러 채널/PLC를 다룰 수 있지만, 여기서는 하나만 정의

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840")

    uri = "http://lee-eunseo-opcua.local"
    idx = await server.register_namespace(uri)

    # 2. 채널, 드라이버, 커넥션 구조 반영 (OPC 서버 내 가상 노드 트리로 표현)
    channels_obj = await server.nodes.objects.add_object(idx, "Channels")
    for ch in CHANNELS:
        ch_node = await channels_obj.add_object(idx, ch["name"])
        driver_node = await ch_node.add_object(idx, "Driver")
        await driver_node.add_property(idx, "Type", ch["driver"])
        conn_node = await ch_node.add_object(idx, "Connection")
        await conn_node.add_property(idx, "Type", ch["connection"])

        # 예시로 채널 하위에 장비 정보/태그도 넣을 수 있음
        device_node = await ch_node.add_object(idx, "Device1")
        await device_node.add_variable(idx, "Status", True, ua.VariantType.Boolean)
        await device_node.add_variable(idx, "Tag1", 1234, ua.VariantType.Int32)

    # 서버 실행 이벤트 로그
    logger.info("[OPC UA Server] active! (channel=%s, driver=%s, connection=%s)", 
                CHANNELS[0]["name"], CHANNELS[0]["driver"], CHANNELS[0]["connection"])

    async with server:
        while True:
            await asyncio.sleep(1)
            # 여기서 장비 상태나 값 업데이트 가능

if __name__ == "__main__":
    asyncio.run(main())

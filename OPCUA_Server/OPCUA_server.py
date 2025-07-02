import asyncio
from asyncua import ua, Server
from Device1_script import Device1Modbus
from modbus_tree_builder import ModbusTreeBuilder

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("Modbus-to-OPCUA Test Server")

    # 트리 구조 생성
    objects = server.get_objects_node()
    channels_node = await objects.add_object(2, "Channels")
    channel1_node = await channels_node.add_object(2, "Channel1-Modbus TCP/IP Ethernet-Ethernet")
    device1_node = await channel1_node.add_object(2, "Device1")
    status_var = await device1_node.add_variable(2, "Status", True)
    tag1_var = await device1_node.add_variable(2, "Tag1", 0)
    await status_var.set_writable()
    await tag1_var.set_writable()

    # === 트리 구조/노드 주소 출력 ===
    print("\n[OPC UA 트리 구조 생성 완료]")
    print("Objects")
    print(" └─Channels")
    print("    └─Channel1-Modbus TCP/IP Ethernet-Ethernet")
    print("       └─Device1")
    print(f"          ├─Status  NodeId: {status_var.nodeid.to_string()}")
    print(f"          └─Tag1    NodeId: {tag1_var.nodeid.to_string()}\n")

    # Modbus 데이터 소스 준비
    device = Device1Modbus()
    asyncio.create_task(device.simulate_data())

    # 1초마다 값 갱신 루프
    async with server:
        while True:
            modbus_data = device.read_all()
            tree = ModbusTreeBuilder(modbus_data).build_tree()
            v_status = tree['Channels']['Channel1-Modbus TCP/IP Ethernet-Ethernet']['Device1']['Status']
            v_tag1 = tree['Channels']['Channel1-Modbus TCP/IP Ethernet-Ethernet']['Device1']['Tag1']
            await status_var.write_value(v_status)
            await tag1_var.write_value(v_tag1)
            print(f"OPCUA에 값 갱신: Status={v_status}, Tag1={v_tag1}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from asyncua import Client

OPCUA_SERVER_URL = "opc.tcp://localhost:4840/"

BROWSE_PATH = [
    "Objects",
    "Channels",
    "Channel1-Modbus TCP/IP Ethernet-Ethernet",
    "Device1"
]
TARGET_VARIABLES = ["Status", "Tag1"]

# --- 트리 전체 출력 함수 ---
async def print_node_tree(node, indent=""):
    bname = await node.read_browse_name()
    print(f"{indent}{bname.Name} ({node.nodeid.to_string()})")
    children = await node.get_children()
    for child in children:
        await print_node_tree(child, indent + "  ")

async def main():
    async with Client(OPCUA_SERVER_URL) as client:
        print(f"[OPCUA CLIENT] 서버 접속: {OPCUA_SERVER_URL}")

        print("\n[서버 노드 트리 구조 전체 출력]")
        await print_node_tree(client.nodes.objects)

        # 트리 경로 따라가서 Device1 노드까지 이동
        node = client.nodes.objects
        for name in BROWSE_PATH[1:]:
            children = await node.get_children()
            found = None
            for child in children:
                bname = await child.read_browse_name()
                if bname.Name == name:
                    found = child
                    break
            if found is None:
                raise Exception(f"노드 '{name}'를 찾을 수 없음!")
            node = found

        # Device1 하위 변수(Status, Tag1) 찾기
        variables = {}
        children = await node.get_children()
        for child in children:
            bname = await child.read_browse_name()
            if bname.Name in TARGET_VARIABLES:
                variables[bname.Name] = child

        if len(variables) < len(TARGET_VARIABLES):
            raise Exception(f"필요한 변수 노드를 모두 찾지 못했습니다! {variables.keys()}")

        print("\n[모니터링 노드]")
        for var in TARGET_VARIABLES:
            print(f"  {var} : NodeId {variables[var].nodeid.to_string()}")

        print("\n--- 실시간 데이터 ---")
        while True:
            vals = {}
            for var in TARGET_VARIABLES:
                vals[var] = await variables[var].read_value()
            print(" | ".join([f"{var}: {vals[var]}" for var in TARGET_VARIABLES]))
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

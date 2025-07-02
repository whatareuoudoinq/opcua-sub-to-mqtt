# ModbusDriver.py
from Device1_script import Device1Modbus

class ModbusDriver:
    """
    주소 기반 장비 데이터를 OPC UA 스타일 트리(dict)로 변환
    """
    def __init__(self, channel_name="Channel1"):
        self.channel_name = channel_name
        self.tree = {}  # 트리 구조

    def build_tree(self, device_name, address_tag_map, data):
        """
        주소-태그명 map, 현재 장비 data dict 받아 트리 생성
        """
        # 채널 > 장비 > 태그:값
        self.tree[self.channel_name] = {
            device_name: {
                tag: data[addr] for addr, tag in address_tag_map.items() if addr in data
            }
        }

    def print_tree(self):
        from pprint import pprint
        pprint(self.tree)

if __name__ == "__main__":
    # 1. 모드버스 장비 객체 생성
    device = Device1Modbus()
    # 2. 주소와 논리태그명 매핑
    address_tag_map = {40001: "Status", 40002: "Tag1"}
    # 3. 시뮬레이션 데이터 한 번만 세팅 (실제 프로젝트는 지속적으로 read_all())
    data = device.read_all()
    # 4. 드라이버에서 트리로 변환
    drv = ModbusDriver()
    drv.build_tree("Device1", address_tag_map, data)
    drv.print_tree()  # 구조 예시 출력

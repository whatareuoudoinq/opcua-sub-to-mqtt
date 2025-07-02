class ModbusTreeBuilder:
    def __init__(self, modbus_data):
        self.modbus_data = modbus_data

    def build_tree(self):
        # 예시: 트리 구조 딕셔너리로 변환
        tree = {
            "Channels": {
                "Channel1-Modbus TCP/IP Ethernet-Ethernet": {
                    "Device1": {
                        "Status": self.modbus_data.get(40001, None),
                        "Tag1": self.modbus_data.get(40002, None),
                    }
                }
            }
        }
        return tree

import sys
import asyncio
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QLabel, QComboBox, QHBoxLayout, QPushButton, QLineEdit, QMessageBox
)
from qasync import QEventLoop, asyncSlot

from opcua_client_mqtt_publisher import main as start_opcua_and_mqtt_clients
from serial_handler import main as start_serial_backend, change_serial_port
from shared_queue import send_queue


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPC UA/Serial/MQTT 통합 모니터")
        self.resize(1000, 700)

        # --- UI 컴포넌트
        self.server_filter = "All Servers"

        # MQTT/OPC UA 서버 선택
        self.server_selector = QComboBox()
        self.server_selector.addItem("All Servers")
        self.server_selector.addItems(["server_test", "server_empty"])
        self.server_selector.currentIndexChanged.connect(self.on_server_selected)

        # 시리얼 포트 입력
        self.serial_port_input = QLineEdit("COM3")
        self.serial_port_input.setFixedWidth(100)
        self.serial_baud_input = QLineEdit("115200")
        self.serial_baud_input.setFixedWidth(100)
        self.serial_connect_btn = QPushButton("시리얼 연결/변경")
        self.serial_connect_btn.clicked.connect(self.on_serial_connect)

        # 출력창
        self.label = QLabel("통합 데이터 출력 영역")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # --- Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("서버 선택:"))
        top_layout.addWidget(self.server_selector)
        top_layout.addSpacing(30)
        top_layout.addWidget(QLabel("시리얼 포트:"))
        top_layout.addWidget(self.serial_port_input)
        top_layout.addWidget(QLabel("Baudrate:"))
        top_layout.addWidget(self.serial_baud_input)
        top_layout.addWidget(self.serial_connect_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.label)
        layout.addWidget(self.output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_server_selected(self, index):
        self.server_filter = self.server_selector.currentText()
        self.output.append(f"🔍 [서버 필터 변경됨: {self.server_filter}]\n")

    def show_message(self, title, text):
        QMessageBox.information(self, title, text)

    def on_serial_connect(self):
        port = self.serial_port_input.text()
        baud = self.serial_baud_input.text()
        try:
            baudrate = int(baud)
        except Exception:
            self.show_message("에러", "Baudrate는 정수여야 합니다.")
            return

        # 시리얼 포트 변경 요청 (비동기 함수는 loop에서 실행)
        asyncio.ensure_future(change_serial_port(port, baudrate))
        self.output.append(f"🖧 [시리얼 연결/변경 요청: {port} {baudrate}]\n")

    @asyncSlot(str)
    async def display_message(self, message: str):
        self.output.append(message)
        self.output.append("-" * 60)


async def gui_loop(window: MainWindow):
    while True:
        if not send_queue.empty():
            msg = await send_queue.get()
            # OPC UA/MQTT/Serial 모든 메시지 공통 처리
            try:
                # MQTT/OPC UA 메시지 구조 (topic 포함)
                if hasattr(msg, 'topic'):  # MqttMessage 타입
                    parsed = json.loads(msg.payload)
                    topic_parts = msg.topic.split("/")
                    server_tag = topic_parts[3] if len(topic_parts) > 3 else "unknown_server"
                    node_id = topic_parts[5] if len(topic_parts) > 5 else "unknown_node"
                    if window.server_filter == "All Servers" or window.server_filter == server_tag:
                        formatted = (
                            f"[MQTT/OPC UA] [Server: {server_tag}] [Node: {node_id}]\n"
                            + json.dumps(parsed, indent=2)
                        )
                        await window.display_message(formatted)
                # SerialMessage 타입
                elif hasattr(msg, 'source') and msg.source == "serial":
                    formatted = (
                        f"[Serial] [Port: {msg.port}]\n"
                        f"Data: {msg.data}"
                    )
                    await window.display_message(formatted)
                else:
                    await window.display_message(f"[RAW] {str(msg)}")
            except Exception:
                await window.display_message(f"[Exception] {msg}")
        await asyncio.sleep(0.1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        # 백엔드 실행
        loop.create_task(start_opcua_and_mqtt_clients())
        loop.create_task(start_serial_backend())
        loop.create_task(gui_loop(window))
        loop.run_forever()


if __name__ == "__main__":
    main()

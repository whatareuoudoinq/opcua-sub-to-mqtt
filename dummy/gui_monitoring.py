import sys
import asyncio
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QLabel, QComboBox, QHBoxLayout, QLineEdit, QPushButton, QMessageBox
)
from qasync import QEventLoop, asyncSlot

from opcua_client_mqtt_publisher import main as start_opcua_and_mqtt_clients
from serial_handler import start_serial_backend
from shared_queue import send_queue

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("로봇-장비 네트워크 통합 모니터링")
        self.resize(1100, 700)
        self.server_filter = "All Servers"
        self.channel_filter = "All"  # "OPC UA", "Serial", "MQTT" 등 확장 가능

        # 서버 필터 드롭다운
        self.server_selector = QComboBox()
        self.server_selector.addItem("All Servers")
        self.server_selector.addItems([
            "server_test", "server_empty"
        ])
        self.server_selector.currentIndexChanged.connect(self.on_server_selected)

        # 통신채널 필터 드롭다운 (시리얼/OPC UA/MQTT)
        self.channel_selector = QComboBox()
        self.channel_selector.addItems(["All", "OPC UA", "Serial"])
        self.channel_selector.currentIndexChanged.connect(self.on_channel_selected)

        # 시리얼 포트 입력부
        self.serial_port_edit = QLineEdit("COM3")
        self.baudrate_edit = QLineEdit("9600")
        self.serial_connect_btn = QPushButton("시리얼 연결")
        self.serial_connect_btn.clicked.connect(self.on_serial_connect_clicked)

        serial_setting_layout = QHBoxLayout()
        serial_setting_layout.addWidget(QLabel("Serial Port:"))
        serial_setting_layout.addWidget(self.serial_port_edit)
        serial_setting_layout.addWidget(QLabel("Baudrate:"))
        serial_setting_layout.addWidget(self.baudrate_edit)
        serial_setting_layout.addWidget(self.serial_connect_btn)

        # 출력부
        self.label = QLabel("통합 수신 데이터 출력 영역")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # 레이아웃 구성
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("서버 선택:"))
        top_layout.addWidget(self.server_selector)
        top_layout.addWidget(QLabel("채널:"))
        top_layout.addWidget(self.channel_selector)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addLayout(serial_setting_layout)
        layout.addWidget(self.label)
        layout.addWidget(self.output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_server_selected(self, index):
        self.server_filter = self.server_selector.currentText()
        self.output.append(f"🔍 [서버 필터 변경됨: {self.server_filter}]\n")

    def on_channel_selected(self, index):
        self.channel_filter = self.channel_selector.currentText()
        self.output.append(f"🔍 [채널 필터 변경됨: {self.channel_filter}]\n")

    def on_serial_connect_clicked(self):
        port = self.serial_port_edit.text()
        baudrate = int(self.baudrate_edit.text())
        # 비동기적으로 시리얼 연결 백엔드 실행 (중복 실행 방지)
        loop = asyncio.get_event_loop()
        loop.create_task(start_serial_backend(port, baudrate))
        QMessageBox.information(self, "Serial 연결", f"{port}@{baudrate} 연결 시도!")

    @asyncSlot(str)
    async def display_message(self, message: str):
        self.output.append(message)
        self.output.append("-" * 60)

async def gui_loop(window: MainWindow):
    while True:
        if not send_queue.empty():
            msg = await send_queue.get()
            # msg 객체에 .channel, .topic, .payload, .server_tag 필드가 들어온다고 가정
            channel = getattr(msg, "channel", "Unknown")
            server_tag = getattr(msg, "server_tag", "unknown_server")

            # 필터링
            if (
                (window.server_filter == "All Servers" or window.server_filter == server_tag)
                and (window.channel_filter == "All" or window.channel_filter == channel)
            ):
                try:
                    parsed = json.loads(msg.payload)
                    formatted = f"[채널: {channel}] [서버: {server_tag}]\n" + json.dumps(parsed, indent=2)
                except Exception:
                    formatted = f"[채널: {channel}] [서버: {server_tag}]\n" + str(msg.payload)
                await window.display_message(formatted)
        await asyncio.sleep(0.2)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.create_task(start_opcua_and_mqtt_clients())
        # 시리얼 포트 자동 연결 X, 버튼 누를 때만 연결
        loop.create_task(gui_loop(window))
        loop.run_forever()

if __name__ == "__main__":
    main()

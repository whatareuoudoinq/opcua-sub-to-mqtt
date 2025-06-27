import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox, QLineEdit
)
from qasync import QEventLoop, asyncSlot

# Dummy function to simulate OPC UA/MQTT start
# Replace with real imports and function calls later
async def start_opcua_and_mqtt():
    while True:
        await asyncio.sleep(1)
        print("[SYSTEM] Simulated OPC UA / MQTT running...")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("로봇-장비 통신 인터페이스 (MQTT / OPC UA)")
        self.resize(900, 700)

        # 시리얼 통신 설정 영역
        self.com_label = QLabel("COM 포트:")
        self.com_select = QComboBox()
        self.com_select.addItems(["COM1", "COM2", "COM3", "COM4"])
        self.baud_label = QLabel("Baudrate:")
        self.baud_input = QLineEdit("9600")
        self.connect_button = QPushButton("연결")
        self.disconnect_button = QPushButton("해제")

        serial_layout = QHBoxLayout()
        serial_layout.addWidget(self.com_label)
        serial_layout.addWidget(self.com_select)
        serial_layout.addWidget(self.baud_label)
        serial_layout.addWidget(self.baud_input)
        serial_layout.addWidget(self.connect_button)
        serial_layout.addWidget(self.disconnect_button)

        # 장비 제어 영역
        self.start_button = QPushButton("작업 시작")
        self.stop_button = QPushButton("작업 정지")
        self.reset_button = QPushButton("에러 리셋")

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)

        # I/O 상태 표시 영역
        self.sensor_label = QLabel("센서 상태: OFF")
        self.error_label = QLabel("에러 상태: 정상")
        self.working_label = QLabel("로봇 동작 중: False")

        io_layout = QVBoxLayout()
        io_layout.addWidget(self.sensor_label)
        io_layout.addWidget(self.error_label)
        io_layout.addWidget(self.working_label)

        # 통신 로그 출력창
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # 전체 레이아웃 구성
        layout = QVBoxLayout()
        layout.addLayout(serial_layout)
        layout.addLayout(control_layout)
        layout.addLayout(io_layout)
        layout.addWidget(QLabel("[통신 로그]"))
        layout.addWidget(self.log_output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 이벤트 연결
        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.start_button.clicked.connect(lambda: self.send_command("Start"))
        self.stop_button.clicked.connect(lambda: self.send_command("Stop"))
        self.reset_button.clicked.connect(lambda: self.send_command("Reset"))

    def connect_serial(self):
        self.log_output.append(f"[INFO] {self.com_select.currentText()} 포트에 연결 시도... (Baud: {self.baud_input.text()})")
        # 실제 시리얼 연결 로직 필요

    def disconnect_serial(self):
        self.log_output.append("[INFO] 시리얼 연결 해제됨.")
        # 실제 연결 종료 로직 필요

    def send_command(self, cmd):
        self.log_output.append(f"[TX] 명령 전송: {cmd}")
        # 실제 시리얼 또는 MQTT/OPC UA로 전송 필요

    @asyncSlot(str)
    async def update_status(self, msg: str):
        self.log_output.append(msg)

async def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.create_task(start_opcua_and_mqtt())
        loop.run_forever()

if __name__ == "__main__":
    asyncio.run(main())

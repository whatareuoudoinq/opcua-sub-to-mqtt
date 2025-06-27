import sys
import asyncio
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel,
    QComboBox, QHBoxLayout, QPushButton, QLineEdit, QMessageBox,
    QListWidget, QTextEdit, QListWidgetItem, QSizePolicy
)
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from qasync import QEventLoop, asyncSlot

from opcua_client_mqtt_publisher import main as start_opcua_and_mqtt_clients
from serial_handler import main as start_serial_backend, change_serial_port
from shared_queue import send_queue


def pretty_json(d):
    if isinstance(d, dict):
        s = json.dumps(d, indent=2, ensure_ascii=False)
        return s
    try:
        return json.dumps(json.loads(d), indent=2, ensure_ascii=False)
    except Exception:
        return str(d)


def parse_topic(topic):
    # 예시: demo/opcua-sub-to-mqtt/server_test/variables/ns=2;i=2
    parts = topic.split("/")
    server = parts[3] if len(parts) > 3 else ""
    channel = parts[4] if len(parts) > 4 else ""
    node = parts[5] if len(parts) > 5 else ""
    return server, channel, node


def message_summary(msg):
    # 메시지 리스트에 보일 요약 정보
    try:
        if hasattr(msg, "topic"):
            server, channel, node = parse_topic(msg.topic)
            parsed = json.loads(msg.payload)
            main_value = parsed.get("Value", {}).get("Value", "")
            status = parsed.get("Status", {}).get("Text", "")
            return f"[{server}] {node} | {main_value} | {status} | {timestamp_str()}"
        elif hasattr(msg, "source") and msg.source == "serial":
            return f"[Serial:{msg.port}] {msg.data[:40]} | {timestamp_str()}"
        else:
            return f"[RAW] {str(msg)[:50]}"
    except Exception as e:
        return f"[EXC] {str(e)}"


def message_detail(msg):
    # 상세 보기용 문자열 (JSON pretty + meta)
    try:
        if hasattr(msg, "topic"):
            server, channel, node = parse_topic(msg.topic)
            parsed = json.loads(msg.payload)
            return (
                f"■ MQTT/OPC UA 메시지\n"
                f"  - 서버: {server}\n  - 채널: {channel}\n  - 노드: {node}\n  - 수신: {timestamp_str()}\n"
                f"  - 토픽: {msg.topic}\n"
                f"{'-'*40}\n"
                f"{pretty_json(parsed)}"
            )
        elif hasattr(msg, "source") and msg.source == "serial":
            return (
                f"■ 시리얼 메시지\n"
                f"  - 포트: {msg.port}\n  - 수신: {timestamp_str()}\n"
                f"{'-'*40}\n"
                f"{msg.data}"
            )
        else:
            return f"[RAW] {str(msg)}"
    except Exception as e:
        return f"[EXCEPTION]\n{str(e)}"


def timestamp_str():
    return datetime.now().strftime("%H:%M:%S")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPC UA/Serial/MQTT 통합 모니터")
        self.resize(1100, 700)

        self.status_label = QLabel("MQTT 상태: -")

        # 필터 상태
        self.server_filter = "All Servers"
        self.channel_filter = "All Channels"
        self.node_filter = "All Nodes"

        # ---- UI 컴포넌트

        # 상단 필터
        self.server_selector = QComboBox()
        self.server_selector.addItem("All Servers")
        self.server_selector.addItems(["server_test", "server_empty"])
        self.server_selector.currentIndexChanged.connect(self.on_server_selected)

        self.channel_selector = QComboBox()
        self.channel_selector.addItem("All Channels")
        # 필요시, 채널 리스트 동적 생성

        self.node_selector = QComboBox()
        self.node_selector.addItem("All Nodes")
        # 필요시, 노드 리스트 동적 생성

        # 시리얼 입력/버튼
        self.serial_port_input = QLineEdit("COM3")
        self.serial_port_input.setFixedWidth(100)
        self.serial_baud_input = QLineEdit("115200")
        self.serial_baud_input.setFixedWidth(100)
        self.serial_connect_btn = QPushButton("시리얼 연결/변경")
        self.serial_connect_btn.clicked.connect(self.on_serial_connect)

        # 리스트/상세
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(430)
        self.list_widget.itemClicked.connect(self.on_message_selected)
        self.detail_widget = QTextEdit()
        self.detail_widget.setReadOnly(True)
        self.detail_widget.setLineWrapMode(QTextEdit.NoWrap)
        self.detail_widget.setMinimumWidth(600)
        self.detail_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("서버:"))
        top_layout.addWidget(self.server_selector)
        top_layout.addSpacing(10)
        top_layout.addWidget(QLabel("채널:"))
        top_layout.addWidget(self.channel_selector)
        top_layout.addSpacing(10)
        top_layout.addWidget(QLabel("노드:"))
        top_layout.addWidget(self.node_selector)
        top_layout.addSpacing(30)
        top_layout.addWidget(QLabel("시리얼 포트:"))
        top_layout.addWidget(self.serial_port_input)
        top_layout.addWidget(QLabel("Baudrate:"))
        top_layout.addWidget(self.serial_baud_input)
        top_layout.addWidget(self.serial_connect_btn)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.list_widget)
        main_layout.addWidget(self.detail_widget)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)        
        layout.addLayout(top_layout)
        layout.addLayout(main_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 내부 메시지 저장
        self.msg_history = []

    def on_server_selected(self, index):
        self.server_filter = self.server_selector.currentText()
        self.apply_filter()

    def on_channel_selected(self, index):
        self.channel_filter = self.channel_selector.currentText()
        self.apply_filter()

    def on_node_selected(self, index):
        self.node_filter = self.node_selector.currentText()
        self.apply_filter()

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
        asyncio.ensure_future(change_serial_port(port, baudrate))
        self.add_to_history(
            SerialMessage(f"[시리얼 연결/변경 요청: {port} {baudrate}]", port)
        )

    def add_to_history(self, msg):
        self.msg_history.append(msg)
        # 최신 메시지 200개로 제한
        if len(self.msg_history) > 200:
            self.msg_history = self.msg_history[-200:]
        self.apply_filter()

    def apply_filter(self):
        # 현재 필터 상태대로 리스트 뿌리기
        self.list_widget.clear()
        for idx, msg in enumerate(reversed(self.msg_history)):
            # 필터 조건
            show = True
            if hasattr(msg, "topic"):
                server, channel, node = parse_topic(msg.topic)
                if self.server_filter != "All Servers" and self.server_filter != server:
                    show = False
                if self.channel_filter != "All Channels" and self.channel_filter != channel:
                    show = False
                if self.node_filter != "All Nodes" and self.node_filter != node:
                    show = False
            if show:
                lw_item = QListWidgetItem(message_summary(msg))
                lw_item.setData(256, len(self.msg_history) - idx - 1)  # 원본 인덱스 저장
                self.list_widget.addItem(lw_item)
        # 최신 메시지 자동 선택
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
            self.show_detail_from_row(0)
        else:
            self.detail_widget.setPlainText("")

    def on_message_selected(self, item):
        idx = item.data(256)
        self.show_detail_from_row(idx)

    def show_detail_from_row(self, idx):
        if idx is not None and 0 <= idx < len(self.msg_history):
            detail = message_detail(self.msg_history[idx])
            self.detail_widget.setPlainText(detail)

    @asyncSlot(str)
    async def display_message(self, message: str):
        self.detail_widget.append(message)
        self.detail_widget.append("-" * 60)


async def gui_loop(window: MainWindow):
    while True:
        if not send_queue.empty():
            msg = await send_queue.get()
            # MQTT 상태 메시지인지 판별
            if hasattr(msg, "type") and msg.type == "mqtt_status":
                # 상태 표시 라벨 갱신
                window.status_label.setText(
                    f"[MQTT 상태] {msg.status} ({msg.time})\n"
                    f"브로커: {msg.broker}:{msg.port}\n"
                    f"토픽: {msg.topics}\n"
                    f"상세: {msg.detail if msg.detail else '-'}"
                )
            else:
                # 일반 메시지(예: 센서 데이터)는 기록 영역에 추가
                window.add_to_history(msg)
        await asyncio.sleep(0.1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.create_task(start_opcua_and_mqtt_clients())
        loop.create_task(start_serial_backend())
        loop.create_task(gui_loop(window))
        loop.run_forever()


# SerialMessage 클래스가 gui에서 바로 쓸 수 있도록(직접 정의/임포트 필요)
class SerialMessage:
    def __init__(self, data, port):
        self.source = "serial"
        self.data = data
        self.port = port

if __name__ == "__main__":
    main()

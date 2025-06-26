import sys
import asyncio
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QLabel, QComboBox, QHBoxLayout
)
from qasync import QEventLoop, asyncSlot

from opcua_client_mqtt_publisher import main as start_opcua_and_mqtt_clients
from shared_queue import send_queue


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPC UA to MQTT Monitor")
        self.resize(900, 600)

        self.server_filter = "All Servers"

        self.label = QLabel("MQTT 수신 데이터 출력 영역")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.server_selector = QComboBox()
        self.server_selector.addItem("All Servers")
        self.server_selector.addItems([
            "server_test", "server_empty"
        ])
        self.server_selector.currentIndexChanged.connect(self.on_server_selected)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("서버 선택:"))
        top_layout.addWidget(self.server_selector)

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

    @asyncSlot(str)
    async def display_message(self, message: str):
        self.output.append(message)
        self.output.append("-" * 60)


async def gui_loop(window: MainWindow):
    while True:
        if not send_queue.empty():
            msg = await send_queue.get()
            try:
                parsed = json.loads(msg.payload)
                topic_parts = msg.topic.split("/")
                server_tag = topic_parts[3] if len(topic_parts) > 3 else "unknown_server"
                node_id = topic_parts[5] if len(topic_parts) > 5 else "unknown_node"

                if window.server_filter == "All Servers" or window.server_filter == server_tag:
                    formatted = (
                        f"[Server: {server_tag}] [Node: {node_id}]\n"
                        + json.dumps(parsed, indent=2)
                    )
                    await window.display_message(formatted)
            except Exception:
                await window.display_message(f"[RAW] {msg.payload}")
        await asyncio.sleep(0.2)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.create_task(start_opcua_and_mqtt_clients())
        loop.create_task(gui_loop(window))
        loop.run_forever()


if __name__ == "__main__":
    main()

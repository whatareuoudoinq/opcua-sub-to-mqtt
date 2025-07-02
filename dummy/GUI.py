import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import time
from asyncua import Client as OpcuaClient
import paho.mqtt.client as mqtt
import json
from collections import deque
from datetime import datetime

OPCUA_SERVER_URL = "opc.tcp://localhost:4840/"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "plc/device1/data"

OPCUA_BROWSE_PATH = [
    "Objects",
    "Channels",
    "Channel1-Modbus TCP/IP Ethernet-Ethernet",
    "Device1"
]
TARGET_VARIABLES = ["Status", "Tag1"]

class OPCUAWorker(threading.Thread):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.daemon = True
        self.should_run = True

    def run(self):
        asyncio.run(self.async_main())

    async def async_main(self):
        async with OpcuaClient(OPCUA_SERVER_URL) as client:
            self.gui.set_opcua_connected(True)
            # 트리 경로로 실제 내 프로젝트 노드만 수집
            mytree = []
            node = client.nodes.objects
            prefix = ""
            mytree.append((prefix, "Objects", node.nodeid.to_string()))
            for name in OPCUA_BROWSE_PATH[1:]:
                found = None
                for child in await node.get_children():
                    bname = await child.read_browse_name()
                    if bname.Name == name:
                        found = child
                        break
                if found is None:
                    break
                prefix += "  "
                mytree.append((prefix, name, found.nodeid.to_string()))
                node = found
            # 하위 변수 추가
            children = await node.get_children()
            for child in children:
                bname = await child.read_browse_name()
                mytree.append((prefix + "  ", bname.Name, child.nodeid.to_string()))
            self.gui.load_opcua_tree(mytree)

            # 주요 변수 노드 찾기
            variables = {}
            for child in children:
                bname = await child.read_browse_name()
                if bname.Name in TARGET_VARIABLES:
                    variables[bname.Name] = child

            while self.should_run:
                for var in TARGET_VARIABLES:
                    val = await variables[var].read_value()
                    nodeid = variables[var].nodeid.to_string()
                    vtype = (await variables[var].read_data_type_as_variant_type()).name
                    ts = time.strftime("%H:%M:%S")
                    self.gui.update_opcua_value(var, nodeid, val, vtype, ts)
                time.sleep(1)
        self.gui.set_opcua_connected(False)
class MQTTWorker(threading.Thread):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.daemon = True
        self.should_run = True

        self.last_msg_time = "-"
        self.last_payload_keys = "-"
        self.msg_count_1min = deque()  # (timestamp, )

    def run(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()
        self.client.subscribe(MQTT_TOPIC)
        while self.should_run:
            # 1초마다 최근 1분 메시지 개수 계산
            now = time.time()
            while self.msg_count_1min and self.msg_count_1min[0] < now - 60:
                self.msg_count_1min.popleft()
            self.gui.update_mqtt_summary(
                connected=self.client.is_connected(),
                broker=f"{MQTT_BROKER}:{MQTT_PORT}",
                topic=MQTT_TOPIC,
                last_msg_time=self.last_msg_time,
                last_payload_keys=self.last_payload_keys,
                msg_count_1min=len(self.msg_count_1min)
            )
            time.sleep(1)
        self.client.loop_stop()

    def on_connect(self, client, userdata, flags, rc):
        self.gui.set_mqtt_connected(rc == 0)

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            self.gui.add_mqtt_log(msg.topic, payload)
            self.last_msg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msg_count_1min.append(time.time())
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    # key와 type을 summary로 표시
                    summary = ", ".join(f"{k} ({type(v).__name__})" for k, v in data.items())
                    self.last_payload_keys = summary
                else:
                    self.last_payload_keys = type(data).__name__
            except Exception:
                self.last_payload_keys = "Payload Parse Error"
        except Exception as e:
            self.gui.add_mqtt_log(msg.topic, f"Decoding Error: {e}")


class IntegratedGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OPC UA & MQTT 통합 모니터링")
        self.geometry("1200x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 좌측 프레임: OPC UA
        left = ttk.Frame(paned, width=600)
        paned.add(left, weight=1)

        # 상단: 값 테이블
        opcua_label = ttk.Label(left, text="OPC UA 실시간 값", font=("Arial", 11, "bold"))
        opcua_label.pack(anchor="nw", pady=(4,2))
        self.opcua_table = ttk.Treeview(left, columns=("nodeid", "value", "type", "ts"), show="headings", height=4)
        for col, w in zip(("nodeid","value","type","ts"), (160, 80, 80, 80)):
            self.opcua_table.heading(col, text=col.capitalize())
            self.opcua_table.column(col, width=w)
        self.opcua_table.pack(fill=tk.X, padx=2)

        # 상태
        self.opcua_status = tk.StringVar(value="Disconnected")
        ttk.Label(left, textvariable=self.opcua_status).pack(anchor="w")

        # 하단: AddressSpace 트리 (내 프로젝트 부분만)
        ttk.Label(left, text="Address Space (내 프로젝트)", font=("Arial", 10)).pack(anchor="w", pady=(10,2))
        self.opcua_tree = ttk.Treeview(left, columns=("nid",), show="tree")
        self.opcua_tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0,8))
        # --- MQTT 패널 ---
        right = ttk.Frame(paned, width=570)
        paned.add(right, weight=1)
        self.mqtt_status = tk.StringVar(value="Disconnected")
        ttk.Label(right, text="MQTT 로그", font=("Arial", 11, "bold")).pack(anchor="nw", pady=(4,2))
        self.mqtt_log = tk.Text(right, height=24, font=("Consolas", 10))
        self.mqtt_log.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, textvariable=self.mqtt_status).pack(anchor="w")

        # ▼▼▼  [개선] MQTT 요약 정보 표시 프레임  ▼▼▼
        self.mqtt_summary = tk.LabelFrame(right, text="브로커/토픽 요약", padx=8, pady=5)
        self.mqtt_summary.pack(fill=tk.X, pady=(8,3), padx=2)
        self.lbl_broker = ttk.Label(self.mqtt_summary, text="Broker: -")
        self.lbl_broker.pack(anchor="w")
        self.lbl_topic = ttk.Label(self.mqtt_summary, text="Subscribed Topic: -")
        self.lbl_topic.pack(anchor="w")
        self.lbl_lastmsg = ttk.Label(self.mqtt_summary, text="Last Message Time: -")
        self.lbl_lastmsg.pack(anchor="w")
        self.lbl_lastfields = ttk.Label(self.mqtt_summary, text="Last Payload Fields: -")
        self.lbl_lastfields.pack(anchor="w")
        self.lbl_msgcount = ttk.Label(self.mqtt_summary, text="Messages (1min): -")
        self.lbl_msgcount.pack(anchor="w")
        # ▲▲▲  [개선]  ▲▲▲

        self.mqtt_vars = {}
        for var in TARGET_VARIABLES:
            lbl = ttk.Label(right, text=f"{var} : 값 -")
            lbl.pack(anchor="w")
            self.mqtt_vars[var] = lbl

        # --- 백그라운드 워커 ---
        self.opcua_worker = OPCUAWorker(self)
        self.mqtt_worker = MQTTWorker(self)
        self.opcua_worker.start()
        self.mqtt_worker.start()

        # 트리에서 노드 선택하면 상단 표에 강조
        self.opcua_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # ▼▼▼ [개선] 요약 정보 업데이트 함수 추가 ▼▼▼
    def update_mqtt_summary(self, connected, broker, topic, last_msg_time, last_payload_keys, msg_count_1min):
        self.lbl_broker.config(text=f"Broker: {broker} {'[Connected]' if connected else '[Disconnected]'}")
        self.lbl_topic.config(text=f"Subscribed Topic: {topic}")
        self.lbl_lastmsg.config(text=f"Last Message Time: {last_msg_time}")
        self.lbl_lastfields.config(text=f"Last Payload Fields: {last_payload_keys}")
        self.lbl_msgcount.config(text=f"Messages (1min): {msg_count_1min}")
    # ▲▲▲
    
    def set_opcua_connected(self, status):
        self.opcua_status.set("Connected" if status else "Disconnected")

    def set_mqtt_connected(self, status):
        self.mqtt_status.set("Connected" if status else "Disconnected")

    def load_opcua_tree(self, tree_list):
        self.opcua_tree.delete(*self.opcua_tree.get_children())
        node_map = {"": ""}
        for prefix, name, nid in tree_list:
            parent = node_map[prefix[:-2]] if len(prefix) > 0 else ""
            item = self.opcua_tree.insert(parent, "end", text=f"{name}", values=(nid,))
            node_map[prefix] = item

    def update_opcua_value(self, var, nodeid, value, vtype, ts):
        found = None
        for item in self.opcua_table.get_children():
            if self.opcua_table.set(item, "nodeid") == nodeid:
                found = item
                break
        if found:
            self.opcua_table.item(found, values=(nodeid, value, vtype, ts))
        else:
            self.opcua_table.insert("", "end", values=(nodeid, value, vtype, ts))

    def add_mqtt_log(self, topic, payload):
        self.mqtt_log.insert(tk.END, f"[{topic}] {payload}\n")
        self.mqtt_log.see(tk.END)

    def update_mqtt_value(self, var, value):
        if var in self.mqtt_vars:
            self.mqtt_vars[var].config(text=f"{var} : 값 {value}")

    def on_tree_select(self, event):
        # 선택한 노드의 NodeId를 표에서 강조(선택 행으로 set)
        sel = self.opcua_tree.focus()
        if sel:
            nid = self.opcua_tree.set(sel, "nid")
            for item in self.opcua_table.get_children():
                if self.opcua_table.set(item, "nodeid") == nid:
                    self.opcua_table.selection_set(item)
                    self.opcua_table.see(item)
                    break

    def on_closing(self):
        self.opcua_worker.should_run = False
        self.mqtt_worker.should_run = False
        self.destroy()

if __name__ == "__main__":
    app = IntegratedGUI()
    app.mainloop()

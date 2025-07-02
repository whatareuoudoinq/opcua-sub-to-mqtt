from sys import platform
from os import name
import asyncio
import json
#from asyncio_mqtt import Client as MqttClient, MqttError
from aiomqtt import Client as MqttClient, MqttError
from typing import Dict
from contextlib import AsyncExitStack
from asyncua import Client, ua, Node
from asyncua.common.events import Event
from asyncua.common.subscription import DataChangeNotif
from datetime import timezone
from datetime import datetime

from shared_queue import send_queue, MQTTStatusMessage

####################################################################################
# Globals:
####################################################################################

# OPC UA Client
#접속할 OPC UA 서버들의 주소  127.0.0.1 → 자기 자신(로컬 PC)에 있는 OPC UA 서버에 접속
# OPC UA 서버별 개별 설정 리스트
server_configs = [
    {
        "server_tag": "server_test",
        "server_url": "opc.tcp://127.0.0.1:4840",
        "nodes_to_subscribe": [
            "ns=2;i=2", 
            "i=2267"
        ],
        "events_to_subscribe": [
            ("ns=2;i=1", "ns=2;i=3")
        ]
    },
    {
        "server_tag": "server_empty",
        "server_url": "opc.tcp://192.168.0.10:4840",
        "nodes_to_subscribe": [
            "ns=2;i=10", 
            "i=3001"
        ],
        "events_to_subscribe": [
            ("ns=2;i=5", "ns=2;i=8")
        ]
    },
]


# MQTT-Settings:
#MQTT 브로커 주소. 여기선 공개 테스트용 브로커인 hivemq 사용
broker_ip = "broker.hivemq.com"
#MQTT 브로커 포트 (기본은 1883, 보안 미적용 시)
broker_port = 1883

class MQTTStatusMessage:
    def __init__(self, status, broker, port, topics, detail=""):
        self.type = "mqtt_status"
        self.status = status  # 예: "CONNECTED", "DISCONNECTED", "ERROR"
        self.broker = broker
        self.port = port
        self.topics = topics
        self.detail = detail
        self.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

####################################################################################
# Factories:
####################################################################################
# MQTT 전송용 JSON 문자열로 바꿈

# OPC UA의 Variant 객체를 딕셔너리로 변환
def makeDictFromVariant(v: ua.Variant):
    '''
    makes a simple dict from Variant-Class 
    ! only for opc ua built in types !
    '''
    # Value 값과 배열 차원 정보, 타입 정보(VariantType) 포함
    return {
        "Value": str(v.Value),
        "ArrayDimensions": str(v.Dimensions),
        "VariantType": {
            "Value": str(v.VariantType.value),
            "Name": str(v.VariantType.name)
        }
    }

# 다국어 메시지를 표현하는 LocalizedText 객체를 JSON용 딕셔너리로 변환
def makeDictFromLocalizedText(lt: ua.LocalizedText):
    return {
        "Locale": str(lt.Locale),
        "Text": str(lt.Text),
    }

# 데이터 품질을 나타내는 StatusCode 객체를 딕셔너리로 변환
def makeDictFromStatusCode(st: ua.StatusCode):
    return {
            "Value": str(st.value),
            "Text": str(st.name),
        }

# 실제 측정값이나 상태를 포함한 DataValue 객체 전체를 변환
# Variant, 상태, 타임스탬프까지 포함된 완전한 구조로 직렬화
def makeDictFromDataValue(dv: ua.DataValue):
    '''
    makes a simple dict from DataValue-Class 
    ! only for opc ua built in types !
    '''
    return {
        "Value": makeDictFromVariant(dv.Value),
        "Status": makeDictFromStatusCode(dv.StatusCode),
        "SourceTimestamp": str(dv.SourceTimestamp.replace(tzinfo=timezone.utc).timestamp()) if dv.SourceTimestamp else None,
        "ServerTimestamp": str(dv.ServerTimestamp.replace(tzinfo=timezone.utc).timestamp()) if dv.ServerTimestamp else None,
    }

# OPC UA 이벤트를 딕셔너리로 변환
def makeDictFromEventData(event: Dict[str, ua.Variant]):
    fields = {
        "EventType": str(event["EventType"].Value.to_string()),
        "SourceName": str(event["SourceName"].Value),
        "SourceNode": str(event["SourceNode"].Value.to_string()),
        "Severity": makeDictFromVariant(event["Severity"]),
        "Message": makeDictFromLocalizedText(event["Message"].Value),   
        "LocalTime": {
            "Offset": str(event["LocalTime"].Value.Offset),
            "DaylightSavingInOffset": str(event["LocalTime"].Value.DaylightSavingInOffset)
        }
    }
    for key in event.keys():
        if key not in ["SourceName", "SourceNode", "Severity", "Message", "LocalTime", "EventType"]:
            fields[key] = makeDictFromVariant(event[key])
    return fields

# 최종적으로 딕셔너리를 JSON 문자열로 직렬화 → MQTT로 publish할 수 있는 형태로 만듦
def makeJsonStringFromDict(d):
    if not isinstance(d, dict): raise ValueError(f"{type(d)} is not a dict!")
    return json.dumps(d)


####################################################################################
# OpcUaClient:
####################################################################################
# OPCUA SERVER에서 전달받은 이벤트나 datachange를 처리하는 콜백 핸들러
class SubscriptionHandler:
    """
    The SubscriptionHandler is used to handle the data that is received for the subscription.
    """

    def __init__(self, server_tag):
        self.server_tag = server_tag
        
    # 서버의 노드 값이 바뀌면 호출됨
    async def datachange_notification(self, node: Node, val, data: DataChangeNotif):
        """
        Callback for asyncua Subscription.
        This method will be called when the Client received a data change message from the Server.
        """
        # 받은 값을 JSON 문자열로 변환하고,
        msg = MqttMessage(
            topic=f"demo/opcua-sub-to-mqtt/{self.server_tag}/variables/{node.nodeid.to_string()}",
            payload=makeJsonStringFromDict(
                makeDictFromDataValue(
                    data.monitored_item.Value
                )
            ),
            qos=1,
            retain=True
        )
        # send_queue에 MqttMessage 형태로 담아 큐에 저장한다. 나중에 MQTT 퍼블리셔가 이 메시지를 브로커에 발행함.
        await send_queue.put(msg)

    # 이벤트 발생 시 호출되어 이벤트 데이터를 마찬가지로 JSON으로 만들어 send_queue에 넣음
    async def event_notification(self, event: Event):
        """
        called for every event notification from server
        """
        fields = event.get_event_props_as_fields_dict()
        msg = MqttMessage(
            topic=f"demo/opcua-sub-to-mqtt/events/{str(event.SourceName).lower()}",
            payload=makeJsonStringFromDict(
                makeDictFromEventData(
                    fields
                )
            ),
            qos=1
        )
        await send_queue.put(msg)

    # 서버 연결 상태가 바뀌었을 때 호출됨 (로그 용도로)
    async def status_change_notification(self, status: ua.StatusChangeNotification):
        """
        called for every status change notification from server
        """
        print("StatusChangeNotification: ", status)
        pass

# OPC UA 서버와 통신하며 상태 관리 및 재연결 수행
async def opcua_client(server_tag, server_url, nodes_to_subscribe, events_to_subscribe):
    """
    Handles connect/disconnect/reconnect/subscribe/unsubscribe
    and connection-monitoring via cyclic service-level read.
    """
    client = Client(url=server_url)
    handler = SubscriptionHandler(server_tag)  # server_tag 전달
    subscription = None
    case = 0
    subscription_handle_list = []

    nodes = []
    if nodes_to_subscribe:
        for node in nodes_to_subscribe:
            nodes.append(client.get_node(node))

    while True:
        if case == 1:
            print(f"[{server_tag}] connecting...")
            try:
                await client.connect()
                print(f"[{server_tag}] connected!")
                case = 2
            except:
                print(f"[{server_tag}] connection error!")
                case = 1
                await asyncio.sleep(2)

        elif case == 2:
            print(f"[{server_tag}] subscribing nodes and events...")
            try:
                subscription = await client.create_subscription(
                    period=2000,
                    handler=handler,
                    publishing=True
                )
                subscription_handle_list = []

                node_handles = await subscription.subscribe_data_change(
                    nodes=nodes,
                    attr=ua.AttributeIds.Value,
                    queuesize=100,
                    monitoring=ua.MonitoringMode.Reporting
                )
                subscription_handle_list.append(node_handles)

                if events_to_subscribe:
                    for event in events_to_subscribe:
                        handle = await subscription.subscribe_events(
                            sourcenode=event[0],
                            evtypes=event[1],
                            evfilter=None,
                            queuesize=50
                        )
                        subscription_handle_list.append(handle)

                print(f"[{server_tag}] subscribed!")
                case = 3
            except:
                print(f"[{server_tag}] subscription error")
                case = 4
                await asyncio.sleep(0)

        elif case == 3:
            try:
                service_level = await client.get_node("ns=0;i=2267").read_value()
                case = 3 if service_level >= 200 else 4
                await asyncio.sleep(2)
            except:
                case = 4

        elif case == 4:
            print(f"[{server_tag}] unsubscribing...")
            try:
                if subscription_handle_list:
                    await subscription.unsubscribe(subscription_handle_list)
                await subscription.delete()
                print(f"[{server_tag}] unsubscribed!")
            except:
                print(f"[{server_tag}] unsubscribing error!")
                subscription = None
                subscription_handle_list = []
                await asyncio.sleep(0)

            print(f"[{server_tag}] disconnecting...")
            try:
                await client.disconnect()
            except:
                print(f"[{server_tag}] disconnection error!")
            case = 0

        else:
            case = 1
            await asyncio.sleep(2)


####################################################################################
# MQTT-Publisher:
####################################################################################

# MQTT로 전송할 메시지를 담기 위한 데이터 구조 클래스
'topic : MQTT에서 메시지를 발행할 경로'
'payload : 발행할 실제 문자열 데이터'
'qos : 메시지 전달 품질 (0~2)'
'retain : 마지막 메시지를 브로커가 기억할지 여부'
class MqttMessage:
    def __init__(self, topic, payload, qos, retain=False):
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain

# MQTT 브로커에 연결하고, 큐에 쌓인 메시지를 발행
async def publisher():
    async with AsyncExitStack() as stack:
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)
        mqtt_client = MqttClient(hostname=broker_ip, port=broker_port)
        try:
            await stack.enter_async_context(mqtt_client)
            # 상태: CONNECTED
            await send_queue.put(MQTTStatusMessage(
                status="CONNECTED", broker=broker_ip, port=broker_port,
                topics="demo/opcua-sub-to-mqtt/#", detail="연결됨"
            ))

            task = asyncio.create_task(publish_messages(mqtt_client, send_queue))
            tasks.add(task)

            await asyncio.gather(*tasks)
        except Exception as e:
            # 상태: ERROR
            await send_queue.put(MQTTStatusMessage(
                status="ERROR", broker=broker_ip, port=broker_port,
                topics="demo/opcua-sub-to-mqtt/#", detail=str(e)
            ))
            raise

# send_queue에서 메시지를 하나씩 꺼내서 MQTT 브로커로 보냄
async def publish_messages(client: MqttClient, queue: asyncio.Queue[MqttMessage]):
    while True:
        get = asyncio.create_task(
            queue.get() # OPC UA 에서 들어온 데이터를 기다림
        )
        done, _ = await asyncio.wait(
            (get, client._disconnected), return_when=asyncio.FIRST_COMPLETED
        )
        if get in done:
            message: MqttMessage = get.result()
            await client.publish(message.topic, message.payload, message.qos, retain=True)
        
async def cancel_tasks(tasks):
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def async_mqtt_client():
    while True:
        try:
            await publisher()
        except MqttError as e:
            print(e)
            await asyncio.sleep(3)

####################################################################################
# Run:
####################################################################################

async def main():
    tasks = []

    for config in server_configs:
        task = asyncio.create_task(
            opcua_client(
                config["server_tag"], 
                config["server_url"],
                config["nodes_to_subscribe"],
                config["events_to_subscribe"]
            )
        )
        tasks.append(task)

    mqtt_task = asyncio.create_task(async_mqtt_client())
    tasks.append(mqtt_task)

    await asyncio.gather(*tasks)


# 이 파일이 스크립트로 직접 실행될 때만 아래 블록을 실행하겠다는 의미. 모듈로 import되었을 경우에는 실행되지 않음.
if __name__ == "__main__":
    if platform.lower() == "win32" or name.lower() == "nt":
        from asyncio import (
            set_event_loop_policy,
            WindowsSelectorEventLoopPolicy
        )
        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

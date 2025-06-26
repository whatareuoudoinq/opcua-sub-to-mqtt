import asyncio
import logging
from asyncua import ua
from asyncua.server import Server, EventGenerator

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')


async def main():
    server = Server()

    #	클라이언트가 접속할 주소 설정
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840")                   ## OPC UA 프로토콜로 접속 가능한 서버를 시작. ip 0.0.0.0으로 설정해서 모든 네트워크 인터페이스에서 접근 허용
    
    #   사용자 네임스페이스 (URI 기반) 등록
    uri = "http://lee-eunseo-opcua.local"                           ## OPC UA의 노드공간인 namespace를 등록하고, 
    idx = await server.register_namespace(uri)
    
    #   MyObject라는 노드(=디바이스/장비) 생성
    myobj = await server.nodes.objects.add_object(idx, "MyObject")  ## 그 아래에 변수 Count를 MYObject라는 노드 안에 생성
    #   그 안에 Count라는 송신 변수와 stop_flag라는 수신 변수 추가
    var = await myobj.add_variable(idx, "Count", 0, ua.VariantType.UInt64)
    stop_flag = await myobj.add_variable(idx, "StopFlag", False, ua.VariantType.Boolean)
    await stop_flag.set_writable()  # 클라이언트가 쓸 수 있도록 설정



    #   사용자 정의 이벤트 타입 생성 (MyFirstEvent)
    etype = await server.create_custom_event_type(        
        idx, 'MyFirstEvent', ua.ObjectIds.BaseEventType,
        [('MyNumericProperty', ua.VariantType.Float),
         ('MyStringProperty', ua.VariantType.String)]
    )
    #   해당 이벤트 타입에 대한 이벤트 생성기 만들기
    myevgen = await server.get_event_generator(etype, myobj)

    # Creating a custom event: Approach 2
    custom_etype = await server.nodes.base_event_type.add_object_type(2, 'MySecondEvent')
    await custom_etype.add_property(idx, 'MyIntProperty', ua.Variant(0, ua.VariantType.Int32))
    await custom_etype.add_property(idx, 'MyBoolProperty', ua.Variant(True, ua.VariantType.Boolean))

    mysecondevgen = await server.get_event_generator(custom_etype, myobj)

    async with server:
        count = 0
        while True:
            await asyncio.sleep(.1)

            # StopFlag 읽기
            stop = await stop_flag.read_value()
            if stop:
                continue  # stop이면 count 증가 안 함

            myevgen.event.Message = ua.LocalizedText("MyFirstEvent %d" % count)
            myevgen.event.Severity = count
            myevgen.event.MyNumericProperty = count
            myevgen.event.MyStringProperty = "Property %d" % count
            #   클라이언트에게 이벤트 전송
            await myevgen.trigger()
            await mysecondevgen.trigger(message="MySecondEvent %d" % count)
            #   Count 변수 값 주기적으로 갱신
            await var.write_value(ua.Variant(count, ua.VariantType.UInt64))
            count += 1


if __name__ == "__main__":
    asyncio.run(main())
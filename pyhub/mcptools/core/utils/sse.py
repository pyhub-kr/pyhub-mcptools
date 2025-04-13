from typing import Optional

import httpx


async def is_mcp_sse_server_alive(sse_url: str, timeout: float = 3.0) -> bool:
    last_event_name: Optional[str] = None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", sse_url, headers={"Accept": "text/event-stream"}) as response:
                if response.status_code != 200:
                    return False
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        last_event_name = line[len("event:") :].strip()
                    elif last_event_name == "endpoint" and line.startswith("data:"):
                        return True  # 이벤트 수신 성공
        return False  # 연결은 됐지만 이벤트 수신 실패
    except httpx.ConnectTimeout:
        # 서버가 너무 느리거나 네트워크 문제로 연결 시간 초과
        return False
    except httpx.ConnectError:
        # 호스트를 찾을 수 없거나 연결 자체 실패
        return False
    except httpx.ReadTimeout:
        # 연결 후 응답이 너무 느려서 중단
        return False
    except httpx.RemoteProtocolError:
        # SSE가 아닌 응답 포맷 등 프로토콜 문제
        return False
    except httpx.HTTPError:
        # 기타 httpx 수준의 예외 (상위 포괄 예외)
        return False

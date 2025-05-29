import asyncio
import inspect
import multiprocessing
import re
from functools import wraps
from typing import Callable

from django.conf import settings
from mcp.server.fastmcp import FastMCP as OrigFastMCP
from mcp.types import AnyFunction

class TaskTimeoutError(Exception):
    """작업 타임아웃 예외"""
    pass


class SyncFunctionNotAllowedError(TypeError):
    """동기 함수가 사용된 경우의 예외"""

    pass




class FastMCP(OrigFastMCP):
    DEFAULT_PROCESS_TIMEOUT = 30

    def _get_function_path(self, fn: Callable) -> tuple[str, str]:
        """함수의 모듈 경로와 이름을 반환합니다."""
        module = inspect.getmodule(fn)
        if module is None:
            raise ValueError(f"Could not determine module for function {fn.__name__}")
        return module.__name__, fn.__name__

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        experimental: bool = False,
        delegator: Callable | None = None,
        timeout: int | None = None,
        enabled: bool | Callable[[], bool] = True,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """MCP 도구를 등록하기 위한 데코레이터입니다.

        Args:
            name (str | None, optional): 도구의 이름. 기본값은 None이며, 이 경우 함수명이 사용됩니다.
            description (str | None, optional): 도구에 대한 설명. 기본값은 None입니다.
            experimental (bool, optional): 실험적 기능 여부. 기본값은 False입니다.
            delegator (Callable | None, optional)
            timeout (int | None, optional): 프로세스 실행 제한 시간(초). 기본값은 None입니다.
            enabled (bool | Callable[[], bool], optional): 도구 활성화 여부. 기본값은 True입니다.

        Returns:
            Callable[[AnyFunction], AnyFunction]: 데코레이터 함수

        Raises:
            TypeError: 장식자가 잘못 사용된 경우
            SyncFunctionNotAllowedError: 동기 함수가 사용된 경우
        """

        if callable(name):
            raise TypeError("The @tool decorator was used incorrectly. Use @tool() instead of @tool")

        # timeout 값 검증 및 조정
        effective_timeout = None
        if delegator is not None:
            if timeout is None:
                effective_timeout = self.DEFAULT_PROCESS_TIMEOUT
            elif timeout <= 0:
                effective_timeout = None  # 타임아웃 비활성화
            else:
                effective_timeout = timeout

        def decorator(fn: AnyFunction) -> AnyFunction:
            if not inspect.iscoroutinefunction(fn):
                raise SyncFunctionNotAllowedError(
                    f"Function {fn.__name__} must be async. Use 'async def' instead of 'def'."
                )

            if delegator is not None:


                # 1) docstring 복사
                fn.__doc__ = delegator.__doc__

                # 2) 타입 힌트(annotations) 복사
                fn.__annotations__ = delegator.__annotations__.copy()  # noqa

                # 3) signature 복사 (default로 지정된 Field(...) 정보 포함)
                sig = inspect.signature(delegator)
                fn.__signature__ = sig

            @wraps(fn)
            async def wrapper(*args, **kwargs):
                if delegator is None:
                    return await fn(*args, **kwargs)

                # 멀티 프로세싱 방식으로 실행하여, timeout이 발생하면 강제 종료
                return execute_with_process_timeout(
                    func=delegator,
                    *args,
                    timeout=effective_timeout,
                    **kwargs,
                )

            if delegator is not None:
                # wrapper에 우리가 덮어쓴 메타를 다시 붙여주기
                wrapper.__doc__ = fn.__doc__
                wrapper.__annotations__ = fn.__annotations__  # noqa
                wrapper.__signature__ = fn.__signature__  # noqa

            if experimental and not settings.EXPERIMENTAL:
                return wrapper

            is_enabled = enabled() if callable(enabled) else enabled
            if not is_enabled:
                return wrapper

            if settings.ONLY_EXPOSE_TOOLS:
                tool_name = name or fn.__name__

                def normalize_name(_name: str) -> str:
                    return _name.replace("-", "_")

                normalized_tool_name = normalize_name(tool_name)
                is_allowed = any(
                    re.fullmatch(normalize_name(pattern), normalized_tool_name)
                    for pattern in settings.ONLY_EXPOSE_TOOLS
                )
                if not is_allowed:
                    return wrapper

            self.add_tool(wrapper, name=name, description=description)
            return wrapper

        return decorator


# 가장 확실한 방법은 별도의 프로세스에서 함수를 실행하고 타임아웃 시 프로세스를 종료하는 것입니다.
# ex) 복잡한 계산, 머신러닝 추론, 외부 바이너리 호출에 적합


def _worker(func, _q, *_args, **_kwargs):
    try:
        result = func(*_args, **_kwargs)
        _q.put((True, result))
    except Exception as e:
        _q.put((False, e))


def execute_with_process_timeout(func, *args, timeout: float = None, **kwargs):
    """
    별도 프로세스에서 func를 실행하고, timeout 초과 시 프로세스를 종료합니다.
    """

    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_worker, args=(func, q, *args), kwargs=kwargs)
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join()
        raise TaskTimeoutError(f"{func.__name__} timed out after {timeout} seconds")

    success, payload = q.get()
    if success:
        return payload
    else:
        raise payload


# 스레드 강제 종료 불가 : cancel()는 태스크 취소 표식만 남기고, 실제로 래핑된 스레드는 계속 실행 → 리소스 누수
# ex) HTTP 요청, DB 조회, 파일 입출력 등


async def execute_with_timeout(func, *args, timeout: float = None, **kwargs):
    """
    sync 함수를 별도 스레드에서 실행하고,
    timeout 초과 시 TaskTimeoutError를 발생시킵니다.
    """
    try:
        # asyncio.to_thread → Python 3.9+ 권장
        return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout)
    except asyncio.TimeoutError:
        raise TaskTimeoutError(f"{func.__name__} timed out after {timeout} seconds")

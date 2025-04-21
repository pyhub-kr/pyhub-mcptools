import asyncio
import inspect
import multiprocessing as mp
import os
import re
from concurrent.futures import TimeoutError
from functools import wraps
from multiprocessing.connection import Connection
from typing import Any, Callable, Optional

import cloudpickle
import django
from django.conf import settings
from mcp.server.fastmcp import FastMCP as OrigFastMCP
from mcp.types import AnyFunction

from pyhub.mcptools.core.utils import activate_timezone


class ProcessTimeoutError(TimeoutError):
    """프로세스 실행 시간 초과 예외"""

    pass


def _process_runner(pipe: Connection, fn_bytes: bytes, args, kwargs) -> None:
    """별도 프로세스에서 함수를 실행하고 결과를 반환하는 헬퍼 함수"""
    try:
        fn = cloudpickle.loads(fn_bytes)
        if inspect.iscoroutinefunction(fn):
            # 비동기 함수인 경우 새로운 이벤트 루프를 생성하여 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(fn(*args, **kwargs))
            finally:
                loop.close()
        else:
            result = fn(*args, **kwargs)
        pipe.send((True, cloudpickle.dumps(result)))
    except Exception as e:
        pipe.send((False, str(e)))


class FastMCP(OrigFastMCP):
    DEFAULT_PROCESS_TIMEOUT = 30  # 30초를 기본값으로 설정

    def _run_in_process(self, fn: Callable, args: tuple, kwargs: dict, timeout: Optional[float]) -> Any:
        """별도 프로세스에서 함수를 실행하고 결과를 반환"""
        parent_conn, child_conn = mp.Pipe()
        fn_bytes = cloudpickle.dumps(fn)

        process = mp.Process(target=_process_runner, args=(child_conn, fn_bytes, args, kwargs))
        process.start()

        if timeout is not None:
            if parent_conn.poll(timeout):
                success, result = parent_conn.recv()
                process.join()
                if success:
                    return cloudpickle.loads(result)
                else:
                    raise RuntimeError(f"Process execution failed: {result}")
            else:
                process.terminate()
                process.join()
                raise ProcessTimeoutError(f"Function {fn.__name__} timed out after {timeout} seconds")
        else:
            success, result = parent_conn.recv()
            process.join()
            if success:
                return cloudpickle.loads(result)
            else:
                raise RuntimeError(f"Process execution failed: {result}")

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        experimental: bool = False,
        enabled: bool | Callable[[], bool] = True,
        run_in_process: bool = False,
        timeout: Optional[float] = None,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """MCP 도구를 등록하기 위한 데코레이터입니다.

        Args:
            name (str | None, optional): 도구의 이름. 기본값은 None이며, 이 경우 함수명이 사용됩니다.
            description (str | None, optional): 도구에 대한 설명. 기본값은 None입니다.
            experimental (bool, optional): 실험적 기능 여부. 기본값은 False입니다.
            enabled (bool | Callable[[], bool], optional): 도구 활성화 여부. 기본값은 True입니다.
            run_in_process (bool, optional): 별도 프로세스에서 실행 여부. 기본값은 False입니다.
            timeout (float | None, optional): 프로세스 실행 제한 시간(초).
                run_in_process=True일 때만 사용됩니다.
                None인 경우 DEFAULT_PROCESS_TIMEOUT(기본 5분)이 적용됩니다.
                0 이하의 값을 지정하면 타임아웃이 비활성화됩니다.

        Returns:
            Callable[[AnyFunction], AnyFunction]: 데코레이터 함수

        Raises:
            TypeError: 데코레이터가 잘못 사용된 경우
            ProcessTimeoutError: 프로세스 실행 시간 초과 시
        """
        if callable(name):
            raise TypeError("The @tool decorator was used incorrectly. Use @tool() instead of @tool")

        # timeout 값 검증 및 조정
        effective_timeout = None
        if run_in_process:
            if timeout is None:
                effective_timeout = self.DEFAULT_PROCESS_TIMEOUT
            elif timeout <= 0:
                effective_timeout = None  # 타임아웃 비활성화
            else:
                effective_timeout = timeout

        def decorator(fn: AnyFunction) -> AnyFunction:
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                if not run_in_process:
                    return await fn(*args, **kwargs)

                _timeout = kwargs.pop("timeout", None) or effective_timeout

                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._run_in_process, fn, args, kwargs, _timeout)

            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                if not run_in_process:
                    return fn(*args, **kwargs)

                _timeout = kwargs.pop("timeout", None) or effective_timeout

                return self._run_in_process(fn, args, kwargs, _timeout)

            wrapper = async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper

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


mcp: FastMCP

if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyhub.mcptools.core.settings")
    django.setup()

    activate_timezone()

    mcp = FastMCP(
        name="pyhub-mcptools",
        # instructions=None,
        # ** settings,
        # debug=settings.DEBUG,
    )


__all__ = ["mcp"]

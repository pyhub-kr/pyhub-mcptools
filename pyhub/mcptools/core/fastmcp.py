import inspect
import re
from functools import wraps
from typing import Callable

from django.conf import settings
from mcp.server.fastmcp import FastMCP as OrigFastMCP
from mcp.types import AnyFunction


class SyncFunctionNotAllowedError(TypeError):
    """동기 함수가 사용된 경우의 예외"""

    pass


class DelegatorNotDecoratedError(TypeError):
    """delegator 함수에 q_task 데코레이터가 적용되지 않은 경우의 예외"""

    pass


class FastMCP(OrigFastMCP):
    DEFAULT_PROCESS_TIMEOUT = 10

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
            DelegatorNotDecoratedError: delegator 함수에 q_task 장식자가 적용되지 않은 경우
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

                if hasattr(delegator, "async_task") is False:
                    raise DelegatorNotDecoratedError(
                        f"Delegator function {delegator.__name__} must be decorated with @q_task"
                    )

                # 1) docstring 복사
                fn.__doc__ = delegator.__doc__

                # 2) 타입 힌트(annotations) 복사
                fn.__annotations__ = delegator.__annotations__.copy()

                # 3) signature 복사 (default로 지정된 Field(...) 정보 포함)
                sig = inspect.signature(delegator)
                fn.__signature__ = sig

            @wraps(fn)
            async def wrapper(*args, **kwargs):
                if delegator is not None and hasattr(delegator, "async_task"):
                    task_result = await delegator.async_task(*args, **kwargs)
                    return await task_result.wait(effective_timeout)

                return await fn(*args, **kwargs)

            if delegator is not None:
                # wrapper에 우리가 덮어쓴 메타를 다시 붙여주기
                wrapper.__doc__ = fn.__doc__
                wrapper.__annotations__ = fn.__annotations__
                wrapper.__signature__ = fn.__signature__

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

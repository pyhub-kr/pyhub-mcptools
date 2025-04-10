import os
from functools import wraps
from typing import Callable

import django
from django.conf import settings
from mcp.server.fastmcp import FastMCP as OrigFastMCP
from mcp.types import AnyFunction

from pyhub.mcptools.core.utils import activate_timezone


class FastMCP(OrigFastMCP):
    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        experimental: bool = False,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """MCP 도구를 등록하기 위한 데코레이터입니다.

        Args:
            name (str | None, optional): 도구의 이름. 기본값은 None이며, 이 경우 함수명이 사용됩니다.
            description (str | None, optional): 도구에 대한 설명. 기본값은 None입니다.
            experimental (bool, optional): 실험적 기능 여부. 기본값은 False입니다.
                True로 설정하면 settings.EXPERIMENTAL이 True일 때만 도구가 등록됩니다.

        Returns:
            Callable[[AnyFunction], AnyFunction]: 데코레이터 함수

        Raises:
            TypeError: 데코레이터가 잘못 사용된 경우 (예: @tool 대신 @tool()을 사용해야 함)

        Example:
            ```python
            @mcp.tool(name="my_tool", description="My tool description")
            def my_tool():
                pass

            # 실험적 기능으로 등록
            @mcp.tool(experimental=True)
            def experimental_tool():
                pass
            ```

        Note:
            experimental=True로 설정된 도구는 settings.EXPERIMENTAL=True인 경우에만
            MCP 도구로 등록되어 사용할 수 있습니다. False인 경우 일반 함수이며 도구로 사용되지 않습니다.
        """
        if callable(name):
            raise TypeError(
                "The @tool decorator was used incorrectly. " "Did you forget to call it? Use @tool() instead of @tool"
            )

        def decorator(fn: AnyFunction) -> AnyFunction:
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            if experimental and not settings.EXPERIMENTAL:
                return wrapper

            self.add_tool(fn, name=name, description=description)
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
    )


__all__ = ["mcp"]
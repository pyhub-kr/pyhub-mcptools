import functools
import inspect
from typing import Any, Callable, TypeVar

from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.utils import applescript_run, applescript_run_sync

F = TypeVar("F", bound=Callable[..., Any])


def macos_excel_request_permission(func: F) -> F:
    """
    macOS에 Microsoft Excel 프로그램에 대한 자동화 (Automation) 권한을 요청하는 장식자
    xlwings를 통한 엑셀 접근에서는 자동화 권한 요청이 들어가지 않습니다.
    직접 AppleScript를 수행해야만 자동화 권한 요청이 들어갑니다.

    Args:
        func: 장식할 함수 (동기/비동기 함수 모두 지원)

    Returns:
        Callable: 원본 함수를 감싸는 장식된 함수

    Note:
        tccutil reset AppleEvents 명령으로 모든 Automation 권한 설정을 초기화할 수 있습니다.
    """

    # macOS 보안정책에 창의 가시성을 조절하거나, 워크북 수를 세는 명령은 자동화 권한을 허용한 앱에서만 가능
    apple_script = """
        tell application "Microsoft Excel"
            get name of workbooks
        end tell
    """

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        if OS.current_is_macos():
            await applescript_run(apple_script)
        return await func(*args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        if OS.current_is_macos():
            applescript_run_sync(apple_script)
        return func(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper  # type: ignore

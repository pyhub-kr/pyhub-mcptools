"""Excel COM 스레드 안정성을 위한 유틸리티"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

from pyhub.mcptools.core.choices import OS

# Windows COM 작업용 스레드 풀 (단일 스레드로 제한)
# COM 객체는 생성된 스레드에서만 사용되어야 하므로 단일 스레드 풀 사용
_excel_com_thread_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Excel-COM-Thread")

T = TypeVar("T")


async def run_in_com_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Windows에서 Excel COM 작업을 전용 스레드에서 실행

    COM 객체는 스레드 친화적이어서 동일한 스레드에서 생성하고 사용해야 합니다.
    이 함수는 모든 Excel COM 작업을 단일 스레드에서 실행하도록 보장합니다.

    Args:
        func: 실행할 함수
        *args: 함수 인자
        **kwargs: 함수 키워드 인자

    Returns:
        함수 실행 결과
    """
    if OS.current_is_windows():
        # Windows에서는 전용 COM 스레드에서 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_excel_com_thread_pool, func, *args, **kwargs)
    else:
        # 다른 OS에서는 일반 스레드에서 실행
        return await asyncio.to_thread(func, *args, **kwargs)

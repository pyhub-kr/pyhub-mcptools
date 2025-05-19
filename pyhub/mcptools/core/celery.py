import time
from enum import StrEnum
from functools import wraps
from typing import Any, Callable, Optional

from asgiref.sync import sync_to_async
from celery import shared_task
from celery.result import AsyncResult as CeleryAsyncResult  # Alias to avoid name clash
import asyncio

from django.conf import settings

from pyhub.mcptools.celery_app import app as celery_app
from pyhub.mcptools.core.choices import CeleryTaskSignal


class TaskStatus(StrEnum):
    """작업 상태를 나타내는 열거형

    CeleryAsyncResult.states 모듈에 의존
    """

    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"
    RETRY = "RETRY"
    IGNORED = "IGNORED"


class AsyncCallableWrapper:
    """비동기 호출 가능한 함수를 래핑하는 클래스.

    Attributes:
        func: 래핑할 함수
    """

    def __init__(self, func: Callable):
        """초기화.

        Args:
            func: 래핑할 함수
        """
        self.func = func
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        """래핑된 함수 직접 호출.

        Args:
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            원본 함수의 실행 결과
        """
        return self.func(*args, **kwargs)

    async def async_task(self, *args, **kwargs) -> "TaskResult":
        """비동기 작업으로 함수 실행.

        Args:
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            TaskResult: 작업 결과 객체
        """

        result = self.func.delay(*args, **kwargs)
        return TaskResult(result.id)


def celery_task(
    queue: Optional[str] = None,
    name: Optional[str] = None,
    rate_limit: Optional[str] = None,
    retry_backoff: bool = True,
    retry_backoff_max: int = 600,
    max_retries: int = 3,
    soft_time_limit: Optional[int] = None,
    time_limit: Optional[int] = None,
    priority: Optional[int] = None,
):
    """
    Celery 작업 데코레이터. @shared_task를 적용하고 기본 큐를 설정합니다.
    **celery_options를 통해 @shared_task의 다른 옵션 전달 가능 (e.g., bind=True)

    Args:
        queue: 작업을 실행할 큐 이름
        name: 작업의 고유 이름. (None: 함수 이름 사용)
        rate_limit: 작업 실행 속도 제한 (예: "100/s", "100/m", "100/h")
        retry_backoff: 재시도 간격을 지수적으로 증가시킬지 여부
        retry_backoff_max: 최대 재시도 간격(초)
        max_retries: 최대 재시도 횟수. (None: 무제한 재시도)
        soft_time_limit: 소프트 타임아웃(초). 이 시간이 지나면 TimeoutError 발생.
                         작업 실행 시간 제한, 정상 종료 유도.
        time_limit: 하드 타임아웃(초). 작업 강제 종료 시간 설정
        priority: 작업 우선순위 (0-255, 높을수록 우선순위 높음)

    Returns:
        AsyncCallableWrapper: 동기/비동기 실행이 가능한 래퍼 객체
    """

    def decorator(func: Callable):
        if queue:
            queue_name = queue
        else:
            queue_name = settings.CELERY_TASK_DEFAULT_QUEUE

        decorated_func = shared_task(
            queue=queue_name,
            name=name,
            rate_limit=rate_limit,
            retry_backoff=retry_backoff,
            retry_backoff_max=retry_backoff_max,
            max_retries=max_retries,
            soft_time_limit=soft_time_limit,
            time_limit=time_limit,
            priority=priority,
        )(func)
        return AsyncCallableWrapper(decorated_func)

    return decorator


class TaskTimeoutError(Exception):
    """작업 대기 시간 초과 시 발생하는 예외"""

    pass


class TaskFailureError(Exception):
    """작업 실패 시 발생하는 예외"""

    pass


# TaskResult class now wraps Celery's AsyncResult
class TaskResult:
    """Celery 작업 결과를 관리하는 클래스."""

    polling_interval: float = 0.1

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._async_result: CeleryAsyncResult[Any] = CeleryAsyncResult(id=task_id, app=celery_app)

    # async def __aenter__(self) -> "TaskResult":
    #     return self

    # async def __aexit__(self, exc_type, exc_value, traceback) -> None:
    #     await self.revoke(terminate=True)

    @property
    def id(self) -> str:
        return self.task_id

    async def wait(
        self,
        timeout: Optional[float] = None,
        raise_exception: bool = True,
        interval: float = 0.1,
        revoke_on_timeout: bool = False,
    ) -> Optional[Any]:
        """작업 완료를 비동기 폴링 방식으로 대기

        Args:
            timeout
            raise_exception
            interval : 폴링 간격
            revoke_on_timeout (book, False) : timeout 발생 시 Task Revoke 여부
        """
        start_time = time.monotonic()
        current_interval = interval  # 초기 폴링 간격
        max_interval = 5.0  # 최대 폴링 간격 (초)
        backoff_factor = 1.1  # 백오프 증가율
        while True:
            # 작업이 최종 상태에 도달하면, 상태를 확인합니다.
            if await self.ready():
                # SUCCESS
                if await self.successful():
                    return await self.result()
                # FAILURE, REVOKED
                else:
                    if raise_exception:
                        original_exception = await self.result()
                        raise TaskFailureError(f"Task {self.id} failed") from original_exception
                    else:
                        return None  # 예외를 발생시키지 않으면 None 반환
            if timeout is not None:
                elapsed_time = time.monotonic() - start_time
                if elapsed_time > timeout:
                    if revoke_on_timeout:
                        await self.revoke(terminate=True)
                    if raise_exception:
                        raise TaskTimeoutError(f"Task {self.id} timed out after {timeout} seconds")
                    else:
                        return None  # 예외를 발생시키지 않으면 None 반환
            await asyncio.sleep(current_interval)
            # 지수적 백오프: 폴링 간격을 점진적으로 증가
            current_interval = min(current_interval * backoff_factor, max_interval)

    async def get_value(self) -> Optional[Any]:
        """성공한 작업의 결과값."""
        if await self.successful():
            return await self.result()
        return None

    async def get_error(self) -> Optional[Any]:  # Can be Exception or traceback string
        """실패한 작업의 오류 정보 (예외 객체 또는 트레이스백)."""
        if await self.failed():
            return await self.result()
        return None

    async def revoke(
        self,
        terminate: bool = False,
        signal: CeleryTaskSignal = CeleryTaskSignal.TERM,
    ) -> None:
        """작업 실행을 취소하거나 실행 중인 작업을 종료"""

        # terminate=True : 강제 종료

        # terminate=False : 취소 요청
        #  - task에서는 주기적으로 self.request.called_directly or self.is_revoked() 여부를 검사하여 안전하게 종료 가능.

        async_func = sync_to_async(self._async_result.revoke, thread_sensitive=True)
        await async_func(terminate=terminate, signal=signal.value)

    async def status(self) -> TaskStatus:
        """Celery 작업 상태를 TaskStatus Enum으로 반환."""

        async_func = sync_to_async(lambda: self._async_result.status, thread_sensitive=True)
        celery_status = await async_func()
        try:
            return TaskStatus(celery_status)
        except ValueError:
            return TaskStatus.PENDING  # Or some other default/unknown status

    async def ready(self) -> bool:
        async_func = sync_to_async(self._async_result.ready, thread_sensitive=True)
        return await async_func()

    async def successful(self) -> bool:
        async_func = sync_to_async(self._async_result.successful, thread_sensitive=True)
        return await async_func()

    async def failed(self) -> bool:
        async_func = sync_to_async(self._async_result.failed, thread_sensitive=True)
        return await async_func()

    async def traceback(self) -> Optional[str]:
        async_func = sync_to_async(lambda: self._async_result.traceback, thread_sensitive=True)
        return await async_func()

    async def result(self) -> Optional[Any]:
        async_func = sync_to_async(lambda: self._async_result.result, thread_sensitive=True)
        return await async_func()

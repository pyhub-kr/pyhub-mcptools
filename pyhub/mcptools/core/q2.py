import asyncio
import time
from enum import StrEnum
from functools import wraps
from typing import Any, Callable, Optional

from asgiref.sync import sync_to_async
from django_q.brokers import get_broker
from django_q.tasks import async_task


class TaskGroup(StrEnum):
    """작업 그룹 식별을 위한 열거형.

    Attributes:
        DEFAULT: 기본 작업 그룹
        XLWINGS: Excel 관련 작업 그룹
    """

    DEFAULT = "default"
    XLWINGS = "xlwings"


class TaskStatus(StrEnum):
    """작업 상태를 나타내는 열거형.

    Attributes:
        FAILURE: 작업 실패
        SUCCESS: 작업 성공
        NOTHING: 작업 대기 중 또는 시간초과
    """

    FAILURE = "failure"
    SUCCESS = "success"
    NOTHING = "nothing"


class AsyncCallableWrapper:
    """비동기 호출 가능한 함수를 래핑하는 클래스.

    Attributes:
        func: 래핑할 함수
        default_group: 기본 작업 그룹
    """

    def __init__(self, func: Callable, default_group: Optional[TaskGroup] = None):
        """초기화.

        Args:
            func: 래핑할 함수
            default_group: 기본 작업 그룹 (선택사항)
        """
        self.func = func
        self.default_group = default_group
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

    async def async_task(
        self,
        *args,
        group: Optional[TaskGroup] = None,
        sync: bool = False,
        hook: Optional[str] = None,
        **kwargs,
    ) -> "TaskResult":
        """비동기 작업으로 함수 실행.

        Args:
            *args: 위치 인자
            group: 작업 그룹 (선택사항)
            sync: 동기 실행 여부 (기본값: False)
            hook: 후크 함수 이름 (선택사항)
            **kwargs: 키워드 인자

        Returns:
            TaskResult: 작업 결과 객체
        """
        path = f"{self.func.__module__}.{self.func.__name__}"
        actual_group = group or self.default_group
        task_id: str = await sync_to_async(async_task)(
            path,
            *args,
            group=actual_group.value if actual_group else None,
            sync=sync,
            hook=hook,
            **kwargs,
        )
        return TaskResult(task_id)


def q_task(group: Optional[TaskGroup] = None):
    """작업 데코레이터.

    Args:
        group: 작업 그룹 (선택사항)

    Returns:
        Callable: 데코레이터 함수

    Raises:
        TypeError: 비동기 함수에 적용할 경우
    """

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"Function {func.__name__} is async. django-q2 only supports synchronous functions as tasks."
            )
        return AsyncCallableWrapper(func, default_group=group)

    return decorator


class TaskTimeoutError(Exception):
    """작업 대기 시간 초과 시 발생하는 예외"""

    pass


class TaskFailureError(Exception):
    """작업 실패 시 발생하는 예외"""

    pass


class TaskResult:
    """작업 결과를 관리하는 클래스.

    Attributes:
        task: 작업 객체
        polling_interval: 상태 확인 간격(초)
        task_id: 작업 ID
    """

    task: Optional = None
    polling_interval: float = 0.1

    def __init__(self, task_id: str):
        """초기화.

        Args:
            task_id: 작업 ID
        """
        self.task_id = task_id

    @property
    def id(self):
        """작업 ID.

        Returns:
            str: 작업 ID
        """
        return self.task_id

    @property
    def status(self) -> TaskStatus:
        """작업 상태.

        Returns:
            TaskStatus: 작업의 현재 상태
        """
        if self.task:
            if self.task.success:
                return TaskStatus.SUCCESS
            else:
                return TaskStatus.FAILURE
        return TaskStatus.NOTHING

    @property
    def attempt_count(self) -> Optional[int]:
        """작업 시도 횟수.

        Returns:
            Optional[int]: 작업 시도 횟수 또는 None
        """
        if self.task:
            return self.task.attempt_count
        return None

    async def wait(
        self,
        timeout: int = 30,
        raise_exception: bool = True,
    ) -> Optional[Any]:
        """작업 완료를 비동기로 대기.

        Args:
            timeout: 대기 시간 제한(초) (기본값: 0, 무제한)
            raise_exception: timeout 또는 작업 실패 시 예외 발생 여부 (기본값: True)

        Returns:
            Optional[Any]: 작업 결과 또는 None

        Raises:
            TaskTimeoutError: timeout이 발생하고 raise_exception이 True인 경우
            TaskFailureError: 작업이 실패하고 raise_exception이 True인 경우
        """
        start_time = time.time()

        while True:
            self.task = await self.get_task()

            if self.task is not None:  # noqa
                if raise_exception and self.status == TaskStatus.FAILURE:
                    raise TaskFailureError(f"Task {self.id} failed with error: {self.error}")
                break

            if timeout > 0 and time.time() - start_time >= timeout:  # noqa
                if raise_exception:
                    raise TaskTimeoutError(f"Task {self.id} timed out after {timeout} seconds")
                break

            await asyncio.sleep(self.polling_interval)

        return self.value

    @property
    def value(self) -> Optional[Any]:
        """작업 결과값.

        Returns:
            Any: 성공한 작업의 결과값 또는 None
        """
        if self.task and self.task.success is True:
            return self.task.result
        return None

    @property
    def error(self) -> Optional[str]:
        """작업 오류 메시지.

        Returns:
            Optional[str]: 실패한 작업의 오류 메시지 또는 None
        """
        if self.task and self.task.success is False:
            return self.task.result
        return None

    @property
    def detail(self) -> str:
        """작업 상세 정보.

        Returns:
            str: 작업의 상세 정보 문자열
        """
        if self.task is None:
            return f"No task for {self.id}"
        else:
            return f"""
Task ID: {self.task.id}
Name: {self.task.name}
Function: {self.task.func}
Hook: {self.task.hook}
Args: {self.task.args}
Kwargs: {self.task.kwargs}
Group: {self.task.group}
Cluster: {self.task.cluster}
Started: {self.task.started}
Stopped: {self.task.stopped}
Success: {self.task.success}
Attempt Count: {self.task.attempt_count}
Result: {self.task.result}
            """.strip()

    async def get_task(self) -> Optional:
        """작업 정보를 비동기로 조회.

        Returns:
            Optional[Task]: 작업 객체 또는 None
        """
        if len(self.id) == 32:
            cond = {"id": self.id}
        else:
            cond = {"name": self.id}

        from django_q.models import Task

        try:
            return await Task.objects.aget(**cond)
        except Task.DoesNotExist:
            return None

    async def retry(self) -> Optional["TaskResult"]:
        """현재 작업을 재시도.

        Returns:
            Optional[TaskResult]: 새로운 작업 결과 객체 또는 None
        """
        if self.status == TaskStatus.NOTHING:
            return None

        task_id: str = await sync_to_async(async_task)(
            self.task.func,
            *self.task.args or [],
            group=self.task.group,
            hook=self.task.hook,
            **self.task.kwargs or {},
        )
        return TaskResult(task_id)

    async def kill(self) -> None:
        """현재 실행 중인 작업을 강제 종료."""
        broker = get_broker()
        await sync_to_async(broker.delete)(self.id)

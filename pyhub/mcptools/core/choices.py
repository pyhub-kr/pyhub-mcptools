import sys

from django.db.models import TextChoices


class FormatChoices(TextChoices):
    JSON = "json"
    TABLE = "table"


class OS(TextChoices):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"

    @classmethod
    def get_current(cls) -> "OS":
        os_system = sys.platform.lower()

        match os_system:
            case os_name if os_name.startswith("win"):
                return cls.WINDOWS
            case os_name if os_name == "darwin":
                return cls.MACOS
            case os_name if os_name == "linux":
                return cls.LINUX
            case _:
                raise ValueError(f"Unsupported operating system {os_system}")

    @classmethod
    def current_is_windows(cls) -> bool:
        return cls.get_current() == cls.WINDOWS

    @classmethod
    def current_is_macos(cls) -> bool:
        return cls.get_current() == cls.MACOS

    @classmethod
    def current_is_linux(cls) -> bool:
        return cls.get_current() == cls.LINUX

    @classmethod
    def get_current_os_type(cls) -> str:
        # .github/workflows/release.yml 에서 명시한 파일명 포맷을 따릅니다.
        current_os = cls.get_current()
        match current_os:
            case OS.WINDOWS:
                return "windows"
            case OS.MACOS:
                return "macOS"
            case OS.LINUX:
                return "linux"

        return "Unknown"


class TransportChoices(TextChoices):
    STDIO = "stdio"
    SSE = "sse"


class McpHostChoices(TextChoices):
    ORIGIN = "origin"
    CLAUDE = "claude"
    CURSOR = "cursor"
    WINDSURF = "windsurf"


class CeleryPoolChoices(TextChoices):
    # 각 worker가 별도의 프로세스로 실행됨. 메모리 격리가 완벽하여 안정성이 높음. CPU-bound 작업에 적합.
    #  - 장점 : 안정성, 메모리 격리, 멀티코어 활용
    #  - 단점 : 프로세스 생성 오버헤드, 메모리 사용량 높음.
    PREFORK = "prefork", "프로세스 기반 Pool"
    # 스레드 기반 pool. 하나의 프로세스 내에서 여러 스레드로 동작. I/O-bound 작업에 적합
    #  - 장점 : 빠른 컨텍스트 스위칭, 적은 메모리 사용
    #  - 단점 : GIL로 인한 CPU-bound 작업 제한. 메모리 격리 없음.
    THREADS = "threads"
    # eventlet 기반의 비동기 pool. 네트워크 I/O가 많은 작업에 최적화. 수천개의 동시 연결 처리 가능.
    # eventlet 라이브러리 설치 필요.
    #  - 장점 : 높은 동시성, 적은 리소스 사용
    #  - 단점 : CPU-bound 작업에 부적합
    EVENTLET = "eventlet"
    # gevent 기반의 비동기 pool. eventlet과 유사한 특성. 네트워크 작업에 최적화. gevent 설치 필요.
    GEVENT = "gevent"
    # 단일 프로세스, 단일 스레드로 동작.
    # 디버깅이나 테스트 목적으로 사용.
    #  - 장점 : 간단한 구조, 디버깅 용이
    #  - 단점 : 성능과 확장성 제한
    SOLO = "solo"


class CeleryLogLevelChoices(TextChoices):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CeleryTaskSignal(TextChoices):
    """작업 종료에 사용할 수 있는 시그널 열거형"""

    TERM = "SIGTERM"  # 정상 종료 요청
    KILL = "SIGKILL"  # 강제 종료
    INT = "SIGINT"  # 인터럽트

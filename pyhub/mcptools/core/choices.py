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
    CLAUDE = "claude"
    # cursor 는 설정 파일 위치를 못 찾았습니다.
    CURSOR = "cursor"

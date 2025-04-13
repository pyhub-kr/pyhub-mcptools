import json
import locale
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer
from django.conf import settings
from django.utils import timezone
from environ import Env
from rich.console import Console
from typer import Exit
from tzlocal import get_localzone

from pyhub.mcptools.core.choices import OS, McpHostChoices

logger = logging.getLogger(__name__)


console = Console()


def make_filecache_setting(
    name: str,
    location_path: Optional[str] = None,
    timeout: Optional[int] = None,
    max_entries: int = 300,
    # 최대치에 도달했을 때 삭제하는 비율 : 3 이면 1/3 삭제, 0 이면 모두 삭제
    cull_frequency: int = 3,
) -> dict:
    if location_path is None:
        location_path = tempfile.gettempdir()

    return {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": f"{location_path}/{name}",
        "TIMEOUT": timeout,
        "OPTIONS": {
            "MAX_ENTRIES": max_entries,
            "CULL_FREQUENCY": cull_frequency,
        },
    }


def get_databases(base_dir: Path):
    env = Env()

    DEFAULT_DATABASE = f"sqlite:///{ base_dir / 'db.sqlite3'}"
    _databases = {
        "default": env.db("DATABASE_URL", default=DEFAULT_DATABASE),
    }

    for key in os.environ.keys():
        if "_DATABASE_URL" in key:
            db_alias = key.replace("_DATABASE_URL", "").lower()
            parsed_config = env.db_url(key)  # 파싱에 실패하면 빈 사전을 반환합니다.
            if parsed_config:
                _databases[db_alias] = parsed_config

    for db_name in _databases:
        if _databases[db_name]["ENGINE"] == "django.db.backends.sqlite3":
            # TODO: sqlite-vec 데이터베이스의 장고 모델을 쓸 때 지정 필요.
            # _databases[db_name]["ENGINE"] = "pyhub.db.backends.sqlite3"

            _databases[db_name].setdefault("OPTIONS", {})

            PRAGMA_FOREIGN_KEYS = env.str("PRAGMA_FOREIGN_KEYS", default="ON")
            PRAGMA_JOURNAL_MODE = env.str("PRAGMA_JOURNAL_MODE", default="WAL")
            PRAGMA_SYNCHRONOUS = env.str("PRAGMA_SYNCHRONOUS", default="NORMAL")
            PRAGMA_BUSY_TIMEOUT = env.int("PRAGMA_BUSY_TIMEOUT", default=5000)
            PRAGMA_TEMP_STORE = env.str("PRAGMA_TEMP_STORE", default="MEMORY")
            PRAGMA_MMAP_SIZE = env.int("PRAGMA_MMAP_SIZE", default=134_217_728)
            PRAGMA_JOURNAL_SIZE_LIMIT = env.int("PRAGMA_JOURNAL_SIZE_LIMIT", default=67_108_864)
            PRAGMA_CACHE_SIZE = env.int("PRAGMA_CACHE_SIZE", default=2000)
            # "IMMEDIATE" or "EXCLUSIVE"
            PRAGMA_TRANSACTION_MODE = env.str("PRAGMA_TRANSACTION_MODE", default="IMMEDIATE")

            init_command = (
                f"PRAGMA foreign_keys={PRAGMA_FOREIGN_KEYS};"
                f"PRAGMA journal_mode = {PRAGMA_JOURNAL_MODE};"
                f"PRAGMA synchronous = {PRAGMA_SYNCHRONOUS};"
                f"PRAGMA busy_timeout = {PRAGMA_BUSY_TIMEOUT};"
                f"PRAGMA temp_store = {PRAGMA_TEMP_STORE};"
                f"PRAGMA mmap_size = {PRAGMA_MMAP_SIZE};"
                f"PRAGMA journal_size_limit = {PRAGMA_JOURNAL_SIZE_LIMIT};"
                f"PRAGMA cache_size = {PRAGMA_CACHE_SIZE};"
            )

            # https://gcollazo.com/optimal-sqlite-settings-for-django/
            _databases[db_name]["OPTIONS"].update(
                {
                    "init_command": init_command,
                    "transaction_mode": PRAGMA_TRANSACTION_MODE,
                }
            )

    return _databases


def activate_timezone(tzname: Optional[str] = None) -> None:
    if tzname is None:
        tzname = getattr(settings, "USER_DEFAULT_TIME_ZONE", None)

    if tzname:
        zone_info = ZoneInfo(tzname)

        try:
            timezone.activate(zone_info)
        except ZoneInfoNotFoundError:
            timezone.deactivate()
    else:
        # If no timezone is found in session or default setting, deactivate
        # to use the default (settings.TIME_ZONE)
        timezone.deactivate()


def get_current_timezone() -> str:
    """현재 운영체제의 TimeZone 문자열을 반환 (ex: 'Asia/Seoul')"""
    return get_localzone().key


def get_current_language_code(default: Literal["en-US", "ko-KR"] = "en-US") -> str:
    lang_code = None

    if OS.current_is_macos():
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleLocale"],
                capture_output=True,
                text=True,
            )
            lang_code = result.stdout.strip()
        except Exception as e:
            logger.exception(e)

    if lang_code is None:
        # 기본 locale 사용
        lang_code, encoding = locale.getlocale()

        if len(lang_code) == 5:
            prefix = lang_code[:2].lower()
            if prefix == "ko":
                lang_code = "ko-KR"
            elif prefix == "en":
                lang_code = "en-US"
            else:
                logger.warning(f"Unknown language code: {lang_code}")
                lang_code = default

    if not lang_code:
        return default

    return lang_code.replace("_", "-")


def get_log_dir_path(mcp_host: McpHostChoices) -> Path:
    current_os = OS.get_current()

    match mcp_host, current_os:
        case McpHostChoices.CLAUDE, OS.WINDOWS:
            dir_path = Path(os.environ["APPDATA"]) / "Claude/logs"
        case McpHostChoices.CLAUDE, OS.MACOS:
            dir_path = Path.home() / "Library/Logs/Claude"
        case _:
            error_msg = f"{current_os.value}의 {mcp_host.value} 프로그램은 지원하지 않습니다."
            console.print(f"[red]{error_msg}[/red]")
            raise typer.Exit(1)

    return dir_path


def get_log_path_list(mcp_host: McpHostChoices) -> list[Path]:
    return list(get_log_dir_path(mcp_host).glob("mcp*.log"))


def get_config_path(
    mcp_host: McpHostChoices,
    is_verbose: bool = False,
    allow_exit: bool = False,
) -> Path:
    """현재 운영체제에 맞는 설정 파일 경로를 반환합니다."""

    current_os = OS.get_current()

    match mcp_host, current_os:
        case McpHostChoices.CLAUDE, OS.WINDOWS:
            config_path = Path(os.environ["APPDATA"]) / "Claude/claude_desktop_config.json"
        case McpHostChoices.CLAUDE, OS.MACOS:
            config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        case McpHostChoices.CURSOR, OS.WINDOWS:
            config_path = Path.home() / ".cursor/mcp.json"
        case McpHostChoices.CURSOR, OS.MACOS:
            config_path = Path.home() / ".cursor/mcp.json"
        case _:
            error_msg = f"{current_os.value}의 {mcp_host.value} 프로그램은 지원하지 않습니다."
            if allow_exit is False:
                raise ValueError(error_msg)
            else:
                console.print(f"[red]{error_msg}[/red]")
                raise typer.Exit(1)

    if is_verbose:
        console.print(f"[INFO] config path : {config_path}", highlight=False)
    return config_path


def read_config_file(path: Path, is_verbose: bool = False) -> dict:
    """설정 파일을 읽어서 반환합니다. with 문에서 사용 가능합니다."""
    if not path.exists():
        raise FileNotFoundError(f"{path} 경로의 파일이 아직 없습니다.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config_data: dict = json.load(f)
            return config_data
    except json.JSONDecodeError as e:
        raise ValueError("JSON 설정 파일에 오류가 있습니다.") from e
    except Exception as e:
        if is_verbose:
            console.print_exception()
        else:
            console.print(f"[red]{type(e).__name__}: {e}[/red]")
        raise Exit(1) from e


def get_editor_commands() -> list[str]:
    """시스템에서 사용 가능한 에디터 명령어 목록을 반환합니다."""

    # 환경 변수에서 기본 에디터 확인
    editors = []

    # VISUAL or EDITOR 환경 변수 확인
    if "VISUAL" in os.environ:
        editors.append(os.environ["VISUAL"])
    if "EDITOR" in os.environ:
        editors.append(os.environ["EDITOR"])

    if sys.platform.startswith("win"):
        editors.extend(["code", "notepad++", "notepad"])
    else:
        editors.extend(["code", "vim", "nano", "emacs", "gedit"])

    return editors


def open_with_default_editor(file_path: Path, is_verbose: bool = False) -> bool:
    """다양한 에디터 명령을 시도하여 파일을 엽니다."""
    file_path_str = str(file_path)

    # 다양한 에디터 명령 시도
    editors = get_editor_commands()
    last_error = None

    for editor in editors:
        try:
            if editor == "code":  # VS Code의 경우 특별 처리
                subprocess.run(["code", "--wait", file_path_str], check=True)
                if is_verbose:
                    console.print("[green]Visual Studio Code 에디터로 파일을 열었습니다.[/green]")
            else:
                subprocess.run([editor, file_path_str], check=True)
                if is_verbose:
                    console.print(f"[green]{editor} 에디터로 파일을 열었습니다.[/green]")
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            last_error = e
            continue

    try:
        match OS.get_current():
            case OS.WINDOWS:
                subprocess.run(["start", file_path_str], shell=True, check=True)
                if is_verbose:
                    console.print("[green]Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            case OS.MACOS:
                subprocess.run(["open", file_path_str], check=True)
                if is_verbose:
                    console.print("[green]macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 모든 시도가 실패한 경우
    error_msg = f"파일을 열 수 있는 에디터를 찾을 수 없습니다. 시도한 에디터: {', '.join(editors)}"
    if last_error:
        error_msg += f"\n마지막 오류: {str(last_error)}"
    return False

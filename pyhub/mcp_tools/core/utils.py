import locale
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone
from environ import Env
from tzlocal import get_localzone

logger = logging.getLogger(__name__)


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

    if sys.platform.lower() == "darwin":  # macOS
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

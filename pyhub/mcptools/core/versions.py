from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

import httpx
from django.core.cache import cache


@dataclass
class VersionCheck:
    installed: str
    latest: str
    has_update: bool


class PackageVersionChecker:
    CACHE_KEY_PREFIX = "pkg_version_check_"
    CACHE_TIMEOUT = 60 * 60 * 0.5  # 30분

    @staticmethod
    def get_installed_version(package_name: str) -> Optional[str]:
        try:
            return version(package_name)
        except PackageNotFoundError:
            return None

    @staticmethod
    def get_latest_version(package_name: str) -> Optional[str]:
        try:
            with httpx.Client(timeout=5.0) as client:  # 컨텍스트 매니저 사용
                response = client.get(f"https://pypi.org/pypi/{package_name}/json")
                response.raise_for_status()
                return response.json()["info"]["version"]
        except (httpx.RequestError, KeyError, ValueError):  # httpx 예외 사용
            return None

    @staticmethod
    def _version_to_tuple(version_str: Optional[str]) -> Optional[tuple]:
        """버전 문자열을 숫자 튜플로 변환"""
        if not version_str:
            return None
        try:
            # 버전 문자열에서 숫자만 추출하여 튜플로 변환
            return tuple(map(int, version_str.split(".")))
        except (ValueError, AttributeError):
            return None

    @classmethod
    def check_update(cls, package: str, is_force: bool = False) -> VersionCheck:
        cache_key = f"{cls.CACHE_KEY_PREFIX}{package}"

        current_installed = cls.get_installed_version(package)

        if is_force:
            cached_version_check = None
        else:
            cached_version_check = cache.get(cache_key)

        if cached_version_check is not None:
            # 캐시된 정보가 있더라도 현재 설치된 버전과 비교
            if cached_version_check.installed != current_installed:
                # 설치된 버전이 변경되었다면 캐시를 무시하고 새로 확인
                cache.delete(cache_key)
            else:
                return cached_version_check

        # 캐시가 없거나 설치 버전이 변경된 경우 새로 확인
        latest = cls.get_latest_version(package)

        # 버전 문자열을 튜플로 변환
        installed_tuple = cls._version_to_tuple(current_installed)
        latest_tuple = cls._version_to_tuple(latest)

        version_check = VersionCheck(
            installed=current_installed,
            latest=latest,
            has_update=(installed_tuple and latest_tuple and latest_tuple > installed_tuple),
        )

        # 결과 캐싱
        cache.set(cache_key, version_check, cls.CACHE_TIMEOUT)

        return version_check

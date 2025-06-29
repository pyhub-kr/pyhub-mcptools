"""Google OAuth 크레덴셜 관리 모듈"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CredentialsManager:
    """Google OAuth 크레덴셜 관리 클래스"""

    def __init__(self):
        self._client_secret_path: Optional[Path] = None

    @property
    def client_secret_path(self) -> Path:
        """클라이언트 시크릿 파일 경로 반환"""
        if self._client_secret_path is not None:
            return self._client_secret_path

        # 캐시된 경로가 없으면 새로 찾기
        self._client_secret_path = self._find_client_secret_path()
        return self._client_secret_path

    def _find_client_secret_path(self) -> Path:
        """클라이언트 시크릿 파일 경로 찾기"""
        from django.conf import settings

        # 1. 환경 변수 확인
        env_path = os.getenv("GOOGLE_CLIENT_SECRET_PATH")
        if env_path and Path(env_path).exists():
            logger.debug(f"환경 변수에서 크레덴셜 찾음: {env_path}")
            return Path(env_path)

        # 2. Django 설정 확인
        if hasattr(settings, "GOOGLE_CLIENT_SECRET_PATH") and settings.GOOGLE_CLIENT_SECRET_PATH:
            settings_path = Path(settings.GOOGLE_CLIENT_SECRET_PATH)
            if settings_path.exists():
                logger.debug(f"Django 설정에서 크레덴셜 찾음: {settings_path}")
                return settings_path

        # 3. 앱 설정 디렉토리 확인
        app_config_dir = self._get_app_config_dir()
        if app_config_dir:
            # 사용자 커스텀 크레덴셜
            user_creds = app_config_dir / "credentials" / "google_client_secret.json"
            if user_creds.exists():
                logger.debug(f"사용자 크레덴셜 사용: {user_creds}")
                return user_creds

            # 기본 크레덴셜 (설치 시 포함)
            default_creds = app_config_dir / "credentials" / "default_google_client_secret.json"
            if default_creds.exists():
                logger.debug(f"기본 크레덴셜 사용 (API 제한): {default_creds}")
                return default_creds

        # 4. 개발 환경용 기본값
        dev_path = Path(__file__).parent.parent / "sheets" / "client_secret.json"
        if dev_path.exists():
            logger.debug(f"개발 크레덴셜 사용: {dev_path}")
            return dev_path

        # 5. 크레덴셜을 찾을 수 없음
        raise FileNotFoundError(
            "Google OAuth 크레덴셜을 찾을 수 없습니다.\n"
            "다음 중 하나를 수행하세요:\n"
            "1. GOOGLE_CLIENT_SECRET_PATH 환경 변수 설정\n"
            "2. Google Cloud Console에서 OAuth 클라이언트 생성 후 설치\n"
            f"3. 크레덴셜을 {app_config_dir / 'credentials' / 'google_client_secret.json'}에 복사"
        )

    def _get_app_config_dir(self) -> Optional[Path]:
        """앱 설정 디렉토리 경로 반환"""
        try:
            import platformdirs

            config_dir = Path(platformdirs.user_config_dir("pyhub-mcptools"))
            if config_dir.exists():
                return config_dir
        except ImportError:
            pass

        # Fallback to home directory
        home_config = Path.home() / ".pyhub-mcptools"
        return home_config if home_config.exists() else home_config

    def get_token_path(self, service: str) -> Path:
        """서비스별 토큰 파일 경로 반환"""
        app_config_dir = self._get_app_config_dir()
        return app_config_dir / "credentials" / f"google_{service}_token.json"

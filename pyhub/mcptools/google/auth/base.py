"""Google 서비스 공통 인증 기본 클래스"""

import logging
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .credentials import CredentialsManager
from .scopes import get_scopes

logger = logging.getLogger(__name__)


class GoogleAuthBase:
    """Google 서비스 공통 인증 기본 클래스"""

    def __init__(self, service: str, scopes: Optional[List[str]] = None):
        """
        Args:
            service: 서비스명 (예: 'sheets', 'gmail', 'combined')
            scopes: 사용할 스코프 목록 (None이면 서비스 기본 스코프 사용)
        """
        self.service = service
        self.scopes = scopes or get_scopes(service)
        self.credentials_manager = CredentialsManager()
        self._credentials: Optional[Credentials] = None

    @property
    def token_path(self) -> Path:
        """토큰 파일 경로"""
        return self.credentials_manager.get_token_path(self.service)

    @property
    def client_secret_path(self) -> Path:
        """클라이언트 시크릿 파일 경로"""
        return self.credentials_manager.client_secret_path

    def get_credentials(self) -> Credentials:
        """인증 정보 조회 및 갱신"""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # 토큰 파일에서 로드 시도
        if self.token_path.exists():
            logger.debug(f"토큰 파일에서 크레덴셜 로드: {self.token_path}")
            self._credentials = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

        # 토큰이 만료되었거나 없으면 갱신/재인증
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                logger.info("토큰을 갱신하는 중...")
                self._credentials.refresh(Request())
            else:
                logger.info("새로운 인증을 시작합니다...")
                self._credentials = self._authenticate()

            # 갱신된 토큰 저장
            self._save_token()

        return self._credentials

    def _authenticate(self) -> Credentials:
        """OAuth 인증 플로우 실행"""
        flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_path), self.scopes)

        # 로컬 서버로 인증 실행
        credentials = flow.run_local_server(port=0)
        logger.info("인증이 완료되었습니다.")
        return credentials

    def _save_token(self) -> None:
        """토큰을 파일에 저장"""
        if not self._credentials:
            return

        # 디렉토리 생성
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        # 토큰 저장
        with open(self.token_path, "w") as token_file:
            token_file.write(self._credentials.to_json())

        # 파일 권한 설정 (보안)
        self.token_path.chmod(0o600)
        logger.debug(f"토큰이 저장되었습니다: {self.token_path}")

    def clear_credentials(self) -> None:
        """저장된 인증 정보 삭제"""
        if self.token_path.exists():
            self.token_path.unlink()
            logger.info(f"토큰 파일이 삭제되었습니다: {self.token_path}")

        self._credentials = None
        logger.info("인증 정보가 삭제되었습니다.")

    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        try:
            credentials = self.get_credentials()
            return credentials and credentials.valid
        except Exception:
            return False

    def get_auth_info(self) -> dict:
        """인증 정보 요약 반환"""
        try:
            credentials = self.get_credentials()
            return {
                "service": self.service,
                "scopes": self.scopes,
                "authenticated": credentials and credentials.valid,
                "token_path": str(self.token_path),
                "client_secret_path": str(self.client_secret_path),
            }
        except Exception as e:
            return {
                "service": self.service,
                "scopes": self.scopes,
                "authenticated": False,
                "error": str(e),
                "token_path": str(self.token_path),
                "client_secret_path": "Not found",
            }


def has_valid_google_credentials(service: str = "sheets") -> bool:
    """Google 서비스의 유효한 credentials 존재 여부 확인

    Args:
        service: Google 서비스명 ('sheets', 'gmail', 'combined')

    Returns:
        bool: 유효한 credentials가 있으면 True
    """
    try:
        auth = GoogleAuthBase(service=service)
        return auth.is_authenticated()
    except Exception:
        return False

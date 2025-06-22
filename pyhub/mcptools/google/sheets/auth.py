"""Google Sheets OAuth 인증 관리

브라우저 기반 OAuth 인증을 처리합니다.
- 사용자별 토큰 관리
- 자동 토큰 갱신 및 재인증
- 안전한 토큰 저장 (홈 디렉토리)
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# OAuth 2.0 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # 읽기/쓰기
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # 파일 목록 조회
]


class GoogleSheetsAuth:
    """Google Sheets 인증 관리자 (싱글톤)"""

    _instance = None
    _credentials: Optional[Credentials] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.creds_dir = Path.home() / ".pyhub-mcptools" / "credentials"
        self.token_file = self.creds_dir / "google_sheets_token.json"

    @property
    def client_secret_path(self) -> Path:
        """클라이언트 시크릿 파일 경로 반환"""
        from django.conf import settings

        # 사용자 정의 경로가 설정된 경우
        if hasattr(settings, "GOOGLE_CLIENT_SECRET_PATH") and settings.GOOGLE_CLIENT_SECRET_PATH:
            return Path(settings.GOOGLE_CLIENT_SECRET_PATH)

        # 기본값: 패키지에 포함된 공용 OAuth 앱
        return Path(__file__).parent / "client_secret.json"

    def get_credentials(self) -> Credentials:
        """인증 정보 반환 (필요시 인증 수행)"""
        # 이미 유효한 인증 정보가 있는 경우
        if self._credentials and self._credentials.valid:
            return self._credentials

        # 저장된 토큰 파일 로드
        if self.token_file.exists():
            try:
                self._credentials = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
                logger.debug("저장된 토큰을 로드했습니다.")
            except Exception as e:
                logger.warning(f"토큰 파일 로드 실패: {e}")
                self._credentials = None

        # 토큰 갱신 또는 새로운 인증
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                # 토큰 갱신 시도
                try:
                    logger.info("토큰을 갱신하는 중...")
                    self._credentials.refresh(Request())
                    self._save_credentials()
                except Exception as e:
                    logger.warning(f"토큰 갱신 실패: {e}")
                    self._credentials = None

            if not self._credentials:
                # 새로운 인증 수행
                self._credentials = self._authenticate()

        return self._credentials

    def _authenticate(self) -> Credentials:
        """브라우저를 통한 OAuth 인증 수행"""
        logger.info("Google Sheets 인증을 시작합니다.")

        # client_secret.json 파일 확인
        if not self.client_secret_path.exists():
            raise AuthenticationError(
                f"클라이언트 시크릿 파일을 찾을 수 없습니다: {self.client_secret_path}\n"
                "Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고 "
                "JSON 파일을 다운로드하세요."
            )

        try:
            # OAuth 플로우 생성
            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_path), SCOPES)

            # 브라우저로 인증 수행
            logger.info("브라우저가 열립니다. Google 계정으로 로그인하세요.")
            credentials = flow.run_local_server(
                port=0,  # 사용 가능한 포트 자동 선택
                success_message="인증 성공! 이 창은 닫으셔도 됩니다.",
                open_browser=True,
            )

            # 토큰 저장
            self._save_credentials(credentials)
            logger.info("인증이 완료되었습니다.")

            return credentials

        except Exception as e:
            raise AuthenticationError(f"인증 중 오류 발생: {e}")

    def _save_credentials(self, credentials: Optional[Credentials] = None) -> None:
        """인증 정보를 파일로 저장"""
        if credentials:
            self._credentials = credentials

        if not self._credentials:
            return

        # 디렉토리 생성
        self.creds_dir.mkdir(parents=True, exist_ok=True)

        # 토큰 저장
        token_data = {
            "token": self._credentials.token,
            "refresh_token": self._credentials.refresh_token,
            "token_uri": self._credentials.token_uri,
            "client_id": self._credentials.client_id,
            "client_secret": self._credentials.client_secret,
            "scopes": self._credentials.scopes,
        }

        with open(self.token_file, "w") as f:
            json.dump(token_data, f, indent=2)

        # 파일 권한 설정 (읽기/쓰기 권한을 소유자만)
        os.chmod(self.token_file, 0o600)
        logger.debug(f"토큰이 저장되었습니다: {self.token_file}")

    def revoke(self) -> None:
        """저장된 인증 정보 삭제"""
        if self.token_file.exists():
            self.token_file.unlink()
            logger.info("저장된 인증 정보가 삭제되었습니다.")

        self._credentials = None


# 전역 인증 관리자 인스턴스
_auth_manager = GoogleSheetsAuth()


def get_credentials() -> Credentials:
    """인증 정보 반환 (공개 함수)"""
    return _auth_manager.get_credentials()


def revoke_credentials() -> None:
    """인증 정보 삭제 (공개 함수)"""
    _auth_manager.revoke()

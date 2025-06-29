"""Google Sheets OAuth 인증 관리

공통 인증 모듈을 사용한 Google Sheets 인증 클래스
- GoogleAuthBase 상속
- 기존 API 호환성 유지
- 자동 토큰 마이그레이션
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials

from ..auth.base import GoogleAuthBase
from ..auth.scopes import SHEETS_SCOPES

logger = logging.getLogger(__name__)


class GoogleSheetsAuth(GoogleAuthBase):
    """Google Sheets 인증 관리자 (싱글톤)"""

    _instance: Optional["GoogleSheetsAuth"] = None

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Google Sheets 인증 초기화"""
        if not hasattr(self, "_initialized"):
            super().__init__(service="sheets", scopes=SHEETS_SCOPES)
            self._initialized = True

            # 기존 토큰 파일 마이그레이션
            self._migrate_legacy_token()

            logger.debug("Google Sheets 인증 클래스가 초기화되었습니다.")

    def _migrate_legacy_token(self) -> None:
        """기존 토큰 파일을 새로운 위치로 마이그레이션"""
        legacy_token_file = Path.home() / ".pyhub-mcptools" / "credentials" / "google_sheets_token.json"

        if legacy_token_file.exists() and not self.token_path.exists():
            try:
                # 기존 토큰 로드
                with open(legacy_token_file, "r") as f:
                    legacy_data = json.load(f)

                # 새 형식으로 변환하여 저장
                credentials = Credentials(
                    token=legacy_data.get("token"),
                    refresh_token=legacy_data.get("refresh_token"),
                    token_uri=legacy_data.get("token_uri"),
                    client_id=legacy_data.get("client_id"),
                    client_secret=legacy_data.get("client_secret"),
                    scopes=legacy_data.get("scopes"),
                )

                # 새 위치에 저장
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, "w") as f:
                    f.write(credentials.to_json())
                self.token_path.chmod(0o600)

                # 기존 파일 삭제
                legacy_token_file.unlink()

                logger.info(f"기존 토큰을 새 위치로 마이그레이션했습니다: {self.token_path}")

            except Exception as e:
                logger.warning(f"토큰 마이그레이션 실패: {e}")

    def test_connection(self) -> bool:
        """Google Sheets API 연결 테스트"""
        try:
            import gspread_asyncio

            credentials = self.get_credentials()
            agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: credentials)

            # 간단한 연결 테스트 (동기 방식으로)
            import asyncio

            async def test() -> bool:
                agc = await agcm.authorize()
                # 사용자가 접근 가능한 첫 번째 스프레드시트 조회 시도
                spreadsheets = await agc.list_spreadsheet_files()
                return len(spreadsheets) >= 0  # 접근 권한만 확인

            result = asyncio.run(test())
            logger.info("Google Sheets 연결 성공!")
            return result

        except Exception as e:
            logger.error(f"Google Sheets 연결 실패: {e}")
            return False


# 전역 인증 관리자 인스턴스
_auth_manager = GoogleSheetsAuth()


def get_credentials() -> Credentials:
    """인증 정보 반환 (공개 함수) - 기존 API 호환성 유지"""
    return _auth_manager.get_credentials()


def revoke_credentials() -> None:
    """인증 정보 삭제 (공개 함수) - 기존 API 호환성 유지"""
    _auth_manager.clear_credentials()

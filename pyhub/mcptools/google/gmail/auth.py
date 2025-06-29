"""Gmail API 인증 클래스"""

import logging
from typing import Optional

from ..auth.base import GoogleAuthBase
from ..auth.scopes import GMAIL_SCOPES

logger = logging.getLogger(__name__)


class GmailAuth(GoogleAuthBase):
    """Gmail API 전용 인증 클래스"""

    _instance: Optional["GmailAuth"] = None

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Gmail 인증 초기화"""
        if not hasattr(self, "_initialized"):
            super().__init__(service="gmail", scopes=GMAIL_SCOPES)
            self._initialized = True
            logger.debug("Gmail 인증 클래스가 초기화되었습니다.")

    def test_connection(self) -> bool:
        """Gmail API 연결 테스트"""
        try:
            from googleapiclient.discovery import build

            credentials = self.get_credentials()
            service = build("gmail", "v1", credentials=credentials)

            # 프로필 정보 조회로 연결 테스트
            profile = service.users().getProfile(userId="me").execute()

            logger.info(f"Gmail 연결 성공! 이메일: {profile.get('emailAddress', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Gmail 연결 실패: {e}")
            return False

    def get_user_email(self) -> Optional[str]:
        """사용자 이메일 주소 조회"""
        try:
            from googleapiclient.discovery import build

            credentials = self.get_credentials()
            service = build("gmail", "v1", credentials=credentials)

            profile = service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress")

        except Exception as e:
            logger.error(f"사용자 이메일 조회 실패: {e}")
            return None

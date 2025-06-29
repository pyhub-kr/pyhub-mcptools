"""Gmail API 관련 예외 클래스"""

from typing import Optional


class GmailAPIError(Exception):
    """Gmail API 기본 예외 클래스"""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class GmailAuthenticationError(GmailAPIError):
    """Gmail API 인증 오류"""

    pass


class GmailPermissionError(GmailAPIError):
    """Gmail API 권한 오류"""

    pass


class GmailQuotaExceededError(GmailAPIError):
    """Gmail API 할당량 초과 오류"""

    pass


class GmailMessageNotFoundError(GmailAPIError):
    """이메일 메시지를 찾을 수 없음"""

    pass


class GmailLabelNotFoundError(GmailAPIError):
    """라벨을 찾을 수 없음"""

    pass


class GmailInvalidQueryError(GmailAPIError):
    """잘못된 검색 쿼리"""

    pass


class GmailInvalidEmailError(GmailAPIError):
    """잘못된 이메일 주소"""

    pass


class GmailSendError(GmailAPIError):
    """이메일 발송 오류"""

    pass

"""Google Sheets 관련 예외 클래스"""


class GoogleSheetsError(Exception):
    """Google Sheets 작업 중 발생하는 기본 예외"""

    pass


class AuthenticationError(GoogleSheetsError):
    """인증 관련 예외"""

    pass


class SpreadsheetNotFoundError(GoogleSheetsError):
    """스프레드시트를 찾을 수 없을 때 발생하는 예외"""

    pass


class RateLimitError(GoogleSheetsError):
    """API 속도 제한에 도달했을 때 발생하는 예외"""

    pass
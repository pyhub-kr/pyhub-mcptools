"""Google Sheets 공통 상수

Google Sheets API 관련 상수들을 중앙에서 관리
"""

# OAuth 2.0 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # 읽기/쓰기
    "https://www.googleapis.com/auth/drive.file",  # 파일 접근
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # 메타데이터 읽기
]

# Google Drive MIME 타입
SPREADSHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"

# 기본 시트 이름 (영어로 표준화)
DEFAULT_SHEET_NAME = "Sheet1"

# API 제한
MAX_BATCH_RANGES = 100  # 배치 작업 시 최대 범위 수
MAX_CELLS_PER_UPDATE = 50000  # 한 번에 업데이트 가능한 최대 셀 수
DEFAULT_CHUNK_SIZE = 1000  # 청크 작업 시 기본 크기

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 초
RETRY_BACKOFF = 2.0  # 지수 백오프 계수

# 캐시 설정
CACHE_TTL = 300  # 5분
MAX_CACHE_SIZE = 100  # 최대 캐시 항목 수

# 시트 크기 기본값
DEFAULT_ROWS = 1000
DEFAULT_COLS = 26

# API 엔드포인트
SHEETS_API_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_API_BASE_URL = "https://www.googleapis.com/drive/v3"

# 에러 메시지
ERROR_MESSAGES = {
    "auth_required": "인증이 필요합니다. 'python -m pyhub.mcptools.google auth'를 실행하세요.",
    "spreadsheet_not_found": "스프레드시트를 찾을 수 없습니다: {spreadsheet_id}",
    "sheet_not_found": "시트를 찾을 수 없습니다: {sheet_name}",
    "invalid_range": "잘못된 범위 형식입니다: {range}",
    "rate_limit": "API 사용 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
    "permission_denied": "권한이 없습니다. 스프레드시트 접근 권한을 확인하세요.",
}

# 정규식 패턴
PATTERNS = {
    "spreadsheet_id": r"^[a-zA-Z0-9-_]+$",
    "cell_address": r"^[A-Z]+\d+$",
    "range": r"^[A-Z]+\d+:[A-Z]+\d+$",
    "sheet_range": r"^(.+)!([A-Z]+\d+(?::[A-Z]+\d+)?)$",
}


# 에러 매칭 패턴 (locale 독립적)
class ErrorPatterns:
    """API 에러 매칭용 키워드 패턴"""

    PERMISSION_KEYWORDS = ["PERMISSION", "DENIED", "ACCESS", "FORBIDDEN", "UNAUTHORIZED"]
    QUOTA_KEYWORDS = ["QUOTA", "LIMIT", "EXHAUSTED", "RESOURCE_EXHAUSTED", "TOO_MANY_REQUESTS"]
    NOT_FOUND_KEYWORDS = ["NOT_FOUND", "DOES_NOT_EXIST", "DOES NOT EXIST", "404", "NOT FOUND"]
    INVALID_KEYWORDS = ["INVALID", "BAD_REQUEST", "MALFORMED", "400"]
    AUTHENTICATION_KEYWORDS = ["UNAUTHENTICATED", "AUTH", "TOKEN", "EXPIRED", "401"]

    @classmethod
    def matches_pattern(cls, error_text: str, pattern_keywords: list) -> bool:
        """에러 텍스트가 패턴에 매칭되는지 확인 (대소문자 무관)"""
        if not error_text:
            return False

        error_upper = error_text.upper()
        return any(keyword in error_upper for keyword in pattern_keywords)


# HTTP 상태 코드별 에러 매핑
HTTP_ERROR_MAPPING = {
    400: "bad_request",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    429: "rate_limit_exceeded",
    500: "internal_server_error",
    503: "service_unavailable",
}

"""Google API 스코프 정의 모듈"""

from typing import List

# Google Sheets API 스코프
SHEETS_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Gmail API 스코프
GMAIL_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
]

# 통합 스코프 (여러 서비스 동시 사용)
COMBINED_SCOPES: List[str] = SHEETS_SCOPES + GMAIL_SCOPES

# 서비스별 스코프 매핑
SERVICE_SCOPES = {
    "sheets": SHEETS_SCOPES,
    "gmail": GMAIL_SCOPES,
    "combined": COMBINED_SCOPES,
}


def get_scopes(service: str) -> List[str]:
    """서비스명으로 스코프 조회"""
    return SERVICE_SCOPES.get(service, [])

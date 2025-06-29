"""Gmail API 관련 상수 정의"""

from enum import Enum
from typing import Dict, List

# Gmail API 버전
GMAIL_API_VERSION = "v1"
GMAIL_API_SERVICE_NAME = "gmail"


# 이메일 상태
class MessageFormat(str, Enum):
    """이메일 메시지 포맷"""

    MINIMAL = "minimal"
    FULL = "full"
    RAW = "raw"
    METADATA = "metadata"


class LabelIds(str, Enum):
    """기본 Gmail 라벨 ID"""

    INBOX = "INBOX"
    SPAM = "SPAM"
    TRASH = "TRASH"
    UNREAD = "UNREAD"
    STARRED = "STARRED"
    IMPORTANT = "IMPORTANT"
    SENT = "SENT"
    DRAFT = "DRAFT"
    CATEGORY_PERSONAL = "CATEGORY_PERSONAL"
    CATEGORY_SOCIAL = "CATEGORY_SOCIAL"
    CATEGORY_PROMOTIONS = "CATEGORY_PROMOTIONS"
    CATEGORY_UPDATES = "CATEGORY_UPDATES"
    CATEGORY_FORUMS = "CATEGORY_FORUMS"


# 검색 쿼리 예시
COMMON_QUERIES: Dict[str, str] = {
    "unread": "is:unread",
    "starred": "is:starred",
    "important": "is:important",
    "from_me": "from:me",
    "to_me": "to:me",
    "has_attachment": "has:attachment",
    "in_inbox": "in:inbox",
    "in_sent": "in:sent",
    "in_trash": "in:trash",
    "is_read": "is:read",
    "today": "newer_than:1d",
    "this_week": "newer_than:7d",
    "this_month": "newer_than:30d",
}

# 최대 조회 수 제한
MAX_RESULTS_LIMIT = 500
DEFAULT_MAX_RESULTS = 10

# MIME 타입
MIME_TYPES: Dict[str, str] = {
    "text": "text/plain",
    "html": "text/html",
    "multipart": "multipart/mixed",
    "alternative": "multipart/alternative",
}

# 헤더 필드
HEADER_FIELDS: List[str] = [
    "From",
    "To",
    "Cc",
    "Bcc",
    "Subject",
    "Date",
    "Message-ID",
    "In-Reply-To",
    "References",
    "Reply-To",
]

# 오류 메시지
ERROR_MESSAGES: Dict[str, str] = {
    "invalid_query": "검색 쿼리가 유효하지 않습니다.",
    "message_not_found": "메시지를 찾을 수 없습니다.",
    "label_not_found": "라벨을 찾을 수 없습니다.",
    "quota_exceeded": "API 사용량 한도를 초과했습니다.",
    "permission_denied": "권한이 없습니다.",
    "invalid_email": "유효하지 않은 이메일 주소입니다.",
}

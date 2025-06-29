"""Google 서비스 공통 인증 모듈"""

from .base import GoogleAuthBase
from .credentials import CredentialsManager
from .scopes import COMBINED_SCOPES, GMAIL_SCOPES, SHEETS_SCOPES

__all__ = [
    "GoogleAuthBase",
    "CredentialsManager",
    "SHEETS_SCOPES",
    "GMAIL_SCOPES",
    "COMBINED_SCOPES",
]

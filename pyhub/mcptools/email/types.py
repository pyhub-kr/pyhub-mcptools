from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class EmailAttachment:
    filename: str
    content_base64: str


@dataclass
class Email:
    identifier: str  # Unique identifier for the email (e.g., message id or index)
    subject: str
    sender_name: str
    sender_email: str
    to: str
    cc: Optional[str]
    received_at: Optional[str]
    attachments: list[EmailAttachment]


class EmailFolderType(Enum):
    INBOX = "INBOX"
    SENT = "SENT"

from dataclasses import dataclass, field
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
    body: Optional[str] = None
    attachments: list[EmailAttachment] = field(default_factory=list)


class EmailFolderType(Enum):
    INBOX = "INBOX"
    SENT = "SENT"

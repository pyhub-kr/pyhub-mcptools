from asgiref.sync import sync_to_async
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.email import apple_mail
from pyhub.mcptools.email import outlook
from pyhub.mcptools.email.types import Email, EmailFolderType
from pyhub.mcptools.email.utils import json_dumps


EXPERIMENTAL = True


@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__list_recent_inbox_emails(
    max_hours: int = Field(
        default=12,
        description="Maximum number of hours to look back for emails",
    ),
    query: str = Field(
        default="",
        description="Search query to filter emails by subject only",
    ),
) -> str:
    """List recent emails from Apple Mail inbox.

    Args:
        max_hours: Maximum number of hours to look back for emails
        query: Search query to filter emails by subject only

    Returns:
        str: JSON string containing list of emails with base64 encoded content
    """

    email_list: list[Email] = await apple_mail.get_emails(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=EmailFolderType.INBOX,
    )
    return json_dumps(email_list, use_base64=True, skip_empty="all")


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__list_recent_inbox_emails(
    max_hours: int = Field(
        default=1,
        description="Maximum number of hours to look back for emails",
    ),
    query: str = Field(
        default="",
        description="Search query to filter emails by subject only",
    ),
) -> str:
    """List recent emails from Outlook inbox.

    Args:
        max_hours: Maximum number of hours to look back for emails
        query: Search query to filter emails by subject only

    Returns:
        str: JSON string containing list of emails with base64 encoded content
    """
    email_list: list[Email] = await sync_to_async(outlook.get_emails, thread_sensitive=True)(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=EmailFolderType.INBOX,
    )
    return json_dumps(email_list, use_base64=True, skip_empty="all")


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__get_email(
    identifier: str = Field(
        description="Unique identifier of the email to retrieve",
    ),
) -> str:
    """Get the body content of a specific email from Outlook.

    Args:
        identifier: Unique identifier of the email to retrieve

    Returns:
        str: Email body content
    """
    email = await sync_to_async(outlook.get_email)(identifier)
    return json_dumps(email, use_base64=True)


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__send_email(
    subject: str = Field(
        description="Subject of the email",
    ),
    message: str = Field(
        description="Plain text message content",
    ),
    from_email: str = Field(
        description="Sender's email address",
    ),
    recipient_list: str = Field(
        description="Comma-separated list of recipient email addresses",
    ),
    html_message: str = Field(
        default="",
        description="HTML message content (optional)",
    ),
    cc_list: str = Field(
        default="",
        description="Comma-separated list of CC recipient email addresses",
    ),
    bcc_list: str = Field(
        default="",
        description="Comma-separated list of BCC recipient email addresses",
    ),
) -> None:
    """Send an email using Outlook.

    Args:
        subject: Subject of the email
        message: Plain text message content
        from_email: Sender's email address
        recipient_list: Comma-separated list of recipient email addresses
        html_message: HTML message content (optional)
        cc_list: Comma-separated list of CC recipient email addresses
        bcc_list: Comma-separated list of BCC recipient email addresses
    """

    await sync_to_async(outlook.send_email, thread_sensitive=EXPERIMENTAL)(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[email.strip() for email in recipient_list.split(",") if email.strip()],
        html_message=html_message or None,
        cc_list=[email.strip() for email in cc_list.split(",") if email.strip()] if cc_list else None,
        bcc_list=[email.strip() for email in bcc_list.split(",") if bcc_list] if bcc_list else None,
    )

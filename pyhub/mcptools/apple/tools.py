"""Apple Mail MCP tools."""

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.apple import mail
from pyhub.mcptools.core.email_types import Email, EmailFolderType
from pyhub.mcptools.core.json_utils import json_dumps


EXPERIMENTAL = True


@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__send_email(
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
        description="HTML message content (optional, will be converted to plain text)",
    ),
    cc_list: str = Field(
        default="",
        description="Comma-separated list of CC recipient email addresses",
    ),
    bcc_list: str = Field(
        default="",
        description="Comma-separated list of BCC recipient email addresses",
    ),
    compose_only: bool = Field(
        default=False,
        description="If true, only open the compose window without sending the email",
    ),
) -> str:
    """Send an email using Apple Mail.

    Args:
        subject: Subject of the email
        message: Plain text message content
        from_email: Sender's email address
        recipient_list: Comma-separated list of recipient email addresses
        html_message: HTML message content (optional, will be converted to plain text)
        cc_list: Comma-separated list of CC recipient email addresses
        bcc_list: Comma-separated list of BCC recipient email addresses
        compose_only: If true, only open the compose window without sending

    Returns:
        Status message describing the result
    """

    send_status_message = await mail.send_email(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,  # Pass string directly
        html_message=html_message or None,
        cc_list=cc_list or None,  # Pass string directly
        bcc_list=bcc_list or None,  # Pass string directly
        compose_only=compose_only,
    )

    return send_status_message


@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__list_emails(
    max_hours: int = Field(
        default=24,
        description="Maximum number of hours to look back for emails",
    ),
    query: str = Field(
        default="",
        description="Optional search query to filter emails",
    ),
    folder: str = Field(
        default="inbox",
        description="Email folder to list (inbox, sent, drafts, trash, or custom folder name)",
    ),
) -> str:
    """List emails from specified Apple Mail folder.

    Args:
        max_hours: Maximum number of hours to look back for emails
        query: Optional search query to filter emails
        folder: Email folder to list (defaults to inbox)

    Returns:
        JSON string containing list of emails with base64 encoded content
    """
    # Map folder parameter to EmailFolderType or custom folder
    folder_type = None
    folder_name = None

    if folder.lower() == "inbox":
        folder_type = EmailFolderType.INBOX
    elif folder.lower() == "sent":
        folder_type = EmailFolderType.SENT
    else:
        # Custom folder name
        folder_name = folder

    email_list: list[Email] = await mail.get_emails(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=folder_type,
        email_folder_name=folder_name,
    )

    return json_dumps(email_list, use_base64=True, skip_empty="all")

"""Outlook MCP tools."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar, Optional, Literal
from asgiref.sync import sync_to_async
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.microsoft import outlook as outlook_module
from pyhub.mcptools.core.email_types import Email, EmailFolderType
from pyhub.mcptools.core.json_utils import json_dumps


EXPERIMENTAL = True

# Windows COM 작업용 스레드 풀 (단일 스레드로 제한)
_com_thread_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="COM-Thread")

T = TypeVar("T")


async def run_with_com_if_windows(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Windows에서는 COM 초기화와 함께 전용 스레드에서 실행하고,
    다른 OS에서는 일반 async로 실행
    """
    if OS.current_is_windows():

        def _run_in_com_thread():
            import pythoncom

            pythoncom.CoInitialize()
            try:
                return func(*args, **kwargs)
            finally:
                pythoncom.CoUninitialize()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_com_thread_pool, _run_in_com_thread)
    else:
        # macOS나 다른 OS에서는 일반 sync_to_async 사용
        return await sync_to_async(func)(*args, **kwargs)


@mcp.tool(experimental=EXPERIMENTAL)
async def outlook(
    operation: Literal["list", "get", "send"] = Field(description="Operation to perform: list, get, or send"),
    # List operation parameters
    max_hours: int = Field(default=24, description="Maximum number of hours to look back for emails"),
    query: Optional[str] = Field(default=None, description="Search query to filter emails by subject"),
    folder: str = Field(
        default="inbox", description="Email folder to list (inbox, sent, drafts, trash, or custom folder name)"
    ),
    # Get operation parameters
    identifier: Optional[str] = Field(default=None, description="Unique identifier of the email to retrieve"),
    # Send operation parameters
    subject: Optional[str] = Field(default=None, description="Subject of the email"),
    message: Optional[str] = Field(default=None, description="Plain text message content"),
    from_email: Optional[str] = Field(default=None, description="Sender's email address"),
    recipient_list: Optional[str] = Field(
        default=None, description="Comma-separated list of recipient email addresses"
    ),
    html_message: Optional[str] = Field(default=None, description="HTML message content (optional)"),
    cc_list: Optional[str] = Field(default=None, description="Comma-separated list of CC recipient email addresses"),
    bcc_list: Optional[str] = Field(default=None, description="Comma-separated list of BCC recipient email addresses"),
    compose_only: bool = Field(default=False, description="If true, only open the compose window without sending"),
) -> str:
    """Interact with Microsoft Outlook for email operations.

    Operations:
    - list: List emails from a specified folder
    - get: Get the content of a specific email
    - send: Send an email (or open compose window)

    Returns:
        JSON string with operation results
    """
    if operation == "list":
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

        email_list: list[Email] = await run_with_com_if_windows(
            outlook_module.get_emails,
            max_hours=max_hours,
            query=query or None,
            email_folder_type=folder_type,
            email_folder_name=folder_name,
        )
        return json_dumps(email_list, use_base64=True, skip_empty="all")

    elif operation == "get":
        # Check if identifier is None or if it's a FieldInfo object (which means it wasn't provided)
        if identifier is None or (hasattr(identifier, "__class__") and identifier.__class__.__name__ == "FieldInfo"):
            return json_dumps({"error": "identifier is required for get operation"})

        email = await run_with_com_if_windows(outlook_module.get_email, identifier)
        return json_dumps(email, use_base64=True)

    elif operation == "send":
        # Validate required fields for send operation
        # Check if any required field is None or FieldInfo (which means it wasn't provided)
        def is_missing(field):
            return field is None or (hasattr(field, "__class__") and field.__class__.__name__ == "FieldInfo")

        if is_missing(subject) or is_missing(message) or is_missing(from_email) or is_missing(recipient_list):
            return json_dumps(
                {"error": "subject, message, from_email, and recipient_list are required for send operation"}
            )

        send_status_message = await run_with_com_if_windows(
            outlook_module.send_email,
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message or None,
            cc_list=cc_list or None,
            bcc_list=bcc_list or None,
            compose_only=compose_only,
        )
        return send_status_message

    else:
        return json_dumps({"error": f"Unknown operation: {operation}"})

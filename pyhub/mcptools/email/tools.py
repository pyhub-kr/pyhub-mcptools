from typing import Optional

from asgiref.sync import sync_to_async

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.email import apple_mail
from pyhub.mcptools.email import outlook
from pyhub.mcptools.email.types import Email, EmailFolderType
from pyhub.mcptools.email.utils import json_dumps


EXPERIMENTAL = True


@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__get_inbox_emails(
    max_hours: int = 12,
    query: str = "",
) -> str:
    email_list: list[Email] = await apple_mail.get_emails(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=EmailFolderType.INBOX,
    )
    return json_dumps(email_list, use_base64=True, skip_empty="all")


@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__get_email_body(
    identifier: str,
    max_hours: int = 12,
) -> str:
    # TODO: apple_mail.get_email_body_mime(identifier) 사용 검토
    # TODO: 반복문을 통해 조회하므로 조회 속도가 느릴 수 밖에 없다? 매칭되는 id가 아니라면 마지막 이메일까지 순회를 돌게 됩니다.
    # spotlight를 통해서는 message id를 통한 직접 조회를 지원?
    return await apple_mail.get_email_body(
        identifier,
        max_hours,
        parse_mime=False,
    )


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__get_inbox_emails(
    max_hours: int = 1,
    query: str = "",
) -> str:
    email_list: list[Email] = await sync_to_async(outlook.get_emails, thread_sensitive=True)(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=EmailFolderType.INBOX,
    )
    return json_dumps(email_list, use_base64=True, skip_empty="all")


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__get_email_body(identifier: str) -> str:
    return await sync_to_async(outlook.get_email_body)(identifier)


@mcp.tool(enabled=OS.current_is_windows(), experimental=EXPERIMENTAL)
async def outlook__send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: list[str],
    html_message: str = "",
    cc_list: Optional[list[str]] = None,
    bcc_list: Optional[list[str]] = None,
) -> None:
    await sync_to_async(outlook.send_email, thread_sensitive=EXPERIMENTAL)(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message or None,
        cc_list=cc_list,
        bcc_list=bcc_list,
    )

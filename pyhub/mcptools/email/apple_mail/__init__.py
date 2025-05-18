from typing import Optional

from pyhub.mcptools.email.types import EmailFolderType, Email
from pyhub.mcptools.email.utils import html_to_text
from pyhub.mcptools.excel.utils import applescript_run
import email
from email import policy


async def get_emails(
    max_hours: int,
    query: Optional[str] = None,
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
) -> list[Email]:

    folder_script = "set theMessages to messages of inbox"
    if email_folder_type == EmailFolderType.SENT:
        folder_script = "set theMessages to messages of sent mailbox"
    elif email_folder_name:
        folder_script = f'set theMessages to messages of mailbox "{email_folder_name}"'

    script = f"""
        tell application "Mail"
            set output to ""
            {folder_script}
            set thresholdAt to (current date) - ({max_hours} * hours)
            repeat with i from 1 to count of theMessages
                set theMessage to item i of theMessages
                set messageDate to date received of theMessage
                if messageDate < thresholdAt then
                    exit repeat
                end if
                set theSubject to subject of theMessage
                set theSender to sender of theMessage
                set theSenderName to extract name from theSender
                set theSenderEmail to extract address from theSender
                set theTo to address of to recipient of theMessage as string
                set theCC to ""
                try
                    set theCC to address of cc recipient of theMessage as string
                end try
                set theDate to date received of theMessage
                set theMessageID to message id of theMessage
                set output to output & "Identifier: " & theMessageID & "\n"
                set output to output & "Subject: " & theSubject & "\n"
                set output to output & "SenderName: " & theSenderName & "\n"
                set output to output & "SenderEmail: " & theSenderEmail & "\n"
                set output to output & "To: " & theTo & "\n"
                set output to output & "CC: " & theCC & "\n"
                set output to output & "ReceivedAt: " & theDate & "\n---\n"
            end repeat
        end tell
        return output
    """

    stdout_str = (await applescript_run(script)).strip()

    emails = []
    current = {}

    def append_current():
        if current:
            emails.append(
                Email(
                    identifier=current.get("Identifier", ""),
                    subject=current.get("Subject", ""),
                    sender_name=current.get("SenderName", ""),
                    sender_email=current.get("SenderEmail", ""),
                    to=current.get("To", ""),
                    cc=current.get("CC"),
                    received_at=current.get("ReceivedAt"),
                    attachments=[],
                )
            )

    for line in stdout_str.splitlines():
        if line == "---":
            append_current()
            current = {}
        elif ": " in line:
            key, value = line.split(": ", 1)
            current[key] = value

    append_current()

    # Python-side query filter
    if query:
        query_lower = query.lower()
        emails = [
            _email
            for _email in emails
            if query_lower in _email.subject.lower()
            or query_lower in (_email.sender_name or "").lower()
            or query_lower in (_email.sender_email or "").lower()
        ]

    return emails


async def get_email_body(identifier: str, max_hours: int, parse_mime: bool = False) -> str:
    """
    Fetch the content of an email by its message id (identifier).
    Searches all mailboxes for the message id.

    Args:
        identifier: The message ID of the email to fetch
        max_hours: Maximum hours to look back for the email
        parse_mime: If True, returns parsed MIME content (html/plain), if False returns raw content

    Returns:
        str: The email content. If parse_mime is True, returns html content if available,
             otherwise returns plain text content. If parse_mime is False, returns raw content.
    """

    script = f"""
        set thresholdDate to (current date) - ({max_hours} * hours)
        tell application "Mail"
            set theMessage to missing value
            repeat with acc in accounts
                repeat with mbx in mailboxes of acc
                    set msgs to (messages of mbx whose message id is "{identifier}")
                    if (count of msgs) > 0 then
                        set theMessage to item 1 of msgs
                        set messageDate to date received of theMessage
                        if messageDate < thresholdDate then
                            set theMessage to missing value
                            exit repeat
                        end if
                        exit repeat
                    end if
                end repeat
                if theMessage is not missing value then exit repeat
            end repeat
            if theMessage is missing value then
                repeat with mbx in mailboxes
                    set msgs to (messages of mbx whose message id is "{identifier}")
                    if (count of msgs) > 0 then
                        set theMessage to item 1 of msgs
                        set messageDate to date received of theMessage
                        if messageDate < thresholdDate then
                            set theMessage to missing value
                            exit repeat
                        end if
                        exit repeat
                    end if
                end repeat
            end if
            if theMessage is not missing value then
                set theSource to source of theMessage
                return theSource
            else
                return ""
            end if
        end tell
    """

    raw_source = (await applescript_run(script)).strip()
    if not raw_source:
        return ""

    if not parse_mime:
        return raw_source

    # Parse MIME content
    raw_bytes = raw_source.encode("utf-8", errors="replace")
    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    plain = None
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and plain is None:
                plain = part.get_content()
            elif ctype == "text/html" and html is None:
                html = part.get_content()
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            plain = msg.get_content()
        elif ctype == "text/html":
            html = msg.get_content()

    if html:
        return html_to_text(html)

    return plain or ""

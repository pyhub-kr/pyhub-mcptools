"""Apple Mail integration."""

from typing import Optional, Union
import email
from email import policy

from pyhub.mcptools.core.email_types import EmailFolderType, Email
from pyhub.mcptools.core.email_utils import parse_email_list
from pyhub.mcptools.microsoft.excel.utils import applescript_run


def html_to_text(html: str) -> str:
    """Convert HTML to plain text."""

    # Simple HTML to text conversion
    # TODO: Use a proper HTML parser like BeautifulSoup
    import re

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)
    # Replace HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


class AppleMailClient:
    def __init__(self):
        self.current_email: dict[str, str] = {}
        self.emails: list[Email] = []

    def _build_applescript(
        self,
        max_hours: int,
        email_folder_type: Optional[EmailFolderType] = None,
        email_folder_name: Optional[str] = None,
        query: Optional[str] = None,
    ) -> str:
        if email_folder_type == EmailFolderType.SENT:
            folder_script = "set theMessages to messages of sent mailbox"
        elif email_folder_name:
            folder_script = f'set theMessages to messages of mailbox "{email_folder_name}"'
        else:
            folder_script = "set theMessages to messages of inbox"

        return f"""
            tell application \"Mail\"
                set outputList to {{}}
                {folder_script}
                set thresholdAt to (current date) - ({max_hours} * hours)
                repeat with theMessage in theMessages
                    try
                        set subjectRaw to subject of theMessage as string
                        set subjectLower to do shell script "echo " & quoted form of subjectRaw & " | tr '[:upper:]' '[:lower:]'"

                        {f'if subjectLower contains "{query.lower()}" then' if query else 'if true then'}
                            set messageDate to date received of theMessage
                            if messageDate < thresholdAt then
                                exit repeat
                            end if

                            -- Get basic message info
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

                            -- Get email content
                            set theContent to ""
                            try
                                set theContent to content of theMessage
                            end try

                            -- Get raw source if available
                            set theSource to ""
                            try
                                set theSource to source of theMessage
                            end try

                            -- Add all fields to the list
                            set end of outputList to "Identifier: " & theMessageID
                            set end of outputList to "Subject: " & subjectRaw
                            set end of outputList to "SenderName: " & theSenderName
                            set end of outputList to "SenderEmail: " & theSenderEmail
                            set end of outputList to "To: " & theTo
                            set end of outputList to "CC: " & theCC
                            set end of outputList to "ReceivedAt: " & theDate
                            set end of outputList to "Content: " & theContent
                            set end of outputList to "RawSource: " & theSource
                            set end of outputList to "<<<EMAIL_DELIMITER>>>"
                        end if
                    end try
                end repeat

                -- Convert list to string with unique delimiter
                set AppleScript's text item delimiters to "<<<FIELD_DELIMITER>>>"
                set output to outputList as string
                return output
            end tell
        """

    def _parse_email_body(self, raw_source: str, content: str) -> str:
        if not raw_source and not content:
            return ""

        # Try to parse MIME content first
        if raw_source:
            try:
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
                if plain:
                    return plain
            except Exception:
                pass  # Fall back to content if MIME parsing fails

        # Fall back to direct content
        if content:
            return content

        return ""

    def _append_current_email(self):
        if self.current_email:
            raw_source = self.current_email.get("RawSource", "")
            content = self.current_email.get("Content", "")
            body = self._parse_email_body(raw_source, content)

            self.emails.append(
                Email(
                    identifier=self.current_email.get("Identifier", ""),
                    subject=self.current_email.get("Subject", ""),
                    sender_name=self.current_email.get("SenderName", ""),
                    sender_email=self.current_email.get("SenderEmail", ""),
                    to=self.current_email.get("To", ""),
                    cc=self.current_email.get("CC"),
                    received_at=self.current_email.get("ReceivedAt"),
                    attachments=[],
                    body=body,
                )
            )

    def _process_output(self, stdout_str: str):
        for line in stdout_str.split("<<<FIELD_DELIMITER>>>"):
            if line == "<<<EMAIL_DELIMITER>>>":
                self._append_current_email()
                self.current_email = {}
            elif ": " in line:
                key, value = line.split(": ", 1)
                self.current_email[key] = value

        self._append_current_email()

    def _filter_emails(self, query: Optional[str]) -> list[Email]:
        if not query:
            return self.emails

        query_lower = query.lower()
        return [
            _email
            for _email in self.emails
            if query_lower in _email.subject.lower()
            or query_lower in (_email.sender_name or "").lower()
            or query_lower in (_email.sender_email or "").lower()
            or query_lower in (_email.body or "").lower()
        ]

    async def get_emails(
        self,
        max_hours: int,
        query: Optional[str] = None,
        email_folder_type: Optional[EmailFolderType] = None,
        email_folder_name: Optional[str] = None,
    ) -> list[Email]:
        script = self._build_applescript(
            max_hours,
            email_folder_type,
            email_folder_name,
            query,
        )

        stdout_str = (await applescript_run(script)).strip()
        self._process_output(stdout_str)

        return self._filter_emails(query)


async def get_emails(
    max_hours: int,
    query: Optional[str] = None,
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
) -> list[Email]:
    client = AppleMailClient()
    return await client.get_emails(max_hours, query, email_folder_type, email_folder_name)


async def send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: Union[str, list[str]],
    html_message: Optional[str] = None,
    cc_list: Optional[Union[str, list[str]]] = None,
    bcc_list: Optional[Union[str, list[str]]] = None,
    connection: Optional[any] = None,  # For compatibility with Outlook
    force_sync: bool = True,  # For compatibility with Outlook
    compose_only: bool = False,
) -> str:
    """Send email via Apple Mail

    Args:
        subject: Email subject
        message: Plain text message
        from_email: Sender email address
        recipient_list: Recipient email addresses (comma-separated string or list)
        html_message: HTML message (currently ignored, uses plain text)
        cc_list: CC recipients (comma-separated string or list)
        bcc_list: BCC recipients (comma-separated string or list)
        connection: Ignored (for compatibility)
        force_sync: Ignored (for compatibility)
        compose_only: If True, opens compose window without sending

    Returns:
        String describing the result of the operation
    """

    # Parse email lists
    recipient_list = parse_email_list(recipient_list)
    cc_list = parse_email_list(cc_list)
    bcc_list = parse_email_list(bcc_list)

    # Escape special characters for AppleScript
    def escape_applescript(text: str) -> str:
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")

    # Use plain text message (Apple Mail AppleScript doesn't support HTML directly)
    body_text = message if message else (html_to_text(html_message) if html_message else "")

    # Build recipient scripts
    to_recipients_script = (
        "\n            ".join(
            [f'make new to recipient with properties {{address:"{addr}"}}' for addr in recipient_list]
        )
        if recipient_list
        else "-- No TO recipients"
    )

    cc_recipients_script = (
        "\n            ".join(
            [f'make new cc recipient with properties {{address:"{addr}"}}' for addr in (cc_list or [])]
        )
        if cc_list
        else "-- No CC recipients"
    )

    bcc_recipients_script = (
        "\n            ".join(
            [f'make new bcc recipient with properties {{address:"{addr}"}}' for addr in (bcc_list or [])]
        )
        if bcc_list
        else "-- No BCC recipients"
    )

    # Determine visibility based on compose_only
    visible_prop = "true" if compose_only else "false"

    script = f"""
    tell application "Mail"
        -- Create new message with specific account
        set newMessage to make new outgoing message with properties {{subject:"{escape_applescript(subject)}", content:"{escape_applescript(body_text)}", visible:{visible_prop}}}

        -- Add recipients
        tell newMessage
            -- Add TO recipients
            {to_recipients_script}

            -- Add CC recipients
            {cc_recipients_script}

            -- Add BCC recipients  
            {bcc_recipients_script}
        end tell

        {"-- Just display the compose window" if compose_only else "-- Send the message"}
        {"activate" if compose_only else "send newMessage"}
        
        return "SUCCESS"
    end tell
    """

    print(script)

    result = await applescript_run(script)

    if "SUCCESS" in result:
        if compose_only:
            return "Email compose window opened successfully. The email is ready for review and manual sending."
        else:
            return "Email sent successfully."
    else:
        return f"Failed to {'open compose window' if compose_only else 'send email'}: {result}"

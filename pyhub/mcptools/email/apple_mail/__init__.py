from typing import Optional

from pyhub.mcptools.email.types import EmailFolderType, Email
from pyhub.mcptools.email.utils import html_to_text
from pyhub.mcptools.excel.utils import applescript_run
import email
from email import policy


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
                            set theCC to \"\"
                            try
                                set theCC to address of cc recipient of theMessage as string
                            end try
                            set theDate to date received of theMessage
                            set theMessageID to message id of theMessage

                            -- Get email content
                            set theContent to \"\"
                            try
                                set theContent to content of theMessage
                            end try

                            -- Get raw source if available
                            set theSource to \"\"
                            try
                                set theSource to source of theMessage
                            end try

                            -- Add all fields to the list
                            set end of outputList to \"Identifier: \" & theMessageID
                            set end of outputList to \"Subject: \" & subjectRaw
                            set end of outputList to \"SenderName: \" & theSenderName
                            set end of outputList to \"SenderEmail: \" & theSenderEmail
                            set end of outputList to \"To: \" & theTo
                            set end of outputList to \"CC: \" & theCC
                            set end of outputList to \"ReceivedAt: \" & theDate
                            set end of outputList to \"Content: \" & theContent
                            set end of outputList to \"RawSource: \" & theSource
                            set end of outputList to \"<<<EMAIL_DELIMITER>>>\"
                        end if
                    end try
                end repeat

                -- Convert list to string with unique delimiter
                set AppleScript's text item delimiters to \"<<<FIELD_DELIMITER>>>\"
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

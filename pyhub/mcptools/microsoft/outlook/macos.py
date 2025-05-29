import base64
import csv
import datetime
import logging
import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional, Generator, Any, Union
from contextlib import contextmanager

import re

from pyhub.mcptools.microsoft.outlook.base import OutlookItemType, OutlookFolderType
from pyhub.mcptools.core.email_types import Email, EmailAttachment, EmailFolderType
from pyhub.mcptools.core.email_utils import parse_email_list
from pyhub.mcptools.microsoft.excel.utils import applescript_run_sync

logger = logging.getLogger(__name__)


@dataclass
class OutlookFolderInfo:
    """macOS Outlook folder information"""

    name: str
    entry_id: str


# macOS doesn't need connection management like Windows
@contextmanager
def outlook_connection() -> Generator[None, None, None]:
    """Compatibility context manager for macOS - does nothing"""
    yield None


def escape_applescript_string(text: str) -> str:
    """Escape string for AppleScript"""
    if text is None:
        return ""
    # Escape backslashes first, then quotes
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def render_template(template_path: Path, context: dict) -> str:
    """Simple template rendering function"""
    with open(template_path, "r") as f:
        content = f.read()

    # Handle includes
    include_pattern = r'{%\s*include\s+[\'"]([^\'"\s]+)[\'"]\s*%}'

    def replace_include(match):
        include_file = match.group(1)
        include_path = template_path.parent / include_file
        if include_path.exists():
            with open(include_path, "r") as f:
                return f.read()
        return ""

    content = re.sub(include_pattern, replace_include, content)

    # Handle if/elif/else conditions
    def process_conditionals(text):
        # Pattern to match complete if/elif/else/endif blocks
        pattern = r"{%\s*if\s+([^%]+)\s*%}(.*?)(?:{%\s*endif\s*%})"

        def replace_conditional(match):
            condition = match.group(1).strip()
            full_content = match.group(2)

            # Split content by elif/else
            parts = re.split(r"{%\s*(elif[^%]*|else)\s*%}", full_content)
            conditions = [condition]

            # Extract elif conditions
            elif_conditions = re.findall(r"{%\s*elif\s+([^%]+)\s*%}", full_content)
            conditions.extend(elif_conditions)

            # Process each condition
            if evaluate_condition(condition, context):
                # Return content before first elif/else
                return parts[0]

            # Check elif conditions
            i = 1
            for elif_cond in elif_conditions:
                i += 2  # Skip the elif marker itself
                if i < len(parts) and evaluate_condition(elif_cond, context):
                    return parts[i]

            # Check for else
            if "{%\s*else\s*%}" in full_content:
                return parts[-1]

            return ""

        return re.sub(pattern, replace_conditional, text, flags=re.DOTALL)

    def evaluate_condition(condition, ctx):
        # Simple condition evaluation
        if "==" in condition:
            var, val = condition.split("==", 1)
            var = var.strip()
            val = val.strip().strip("'\"")
            return ctx.get(var) == val
        else:
            # Simple variable check
            return bool(ctx.get(condition.strip()))

    content = process_conditionals(content)

    # Handle for loops
    for_pattern = r"{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}"

    def replace_for(match):
        item_name = match.group(1)
        list_name = match.group(2)
        loop_content = match.group(3)
        items = context.get(list_name, [])
        result = []
        for item in items:
            item_context = context.copy()
            item_context[item_name] = item
            # Replace variables in loop content
            item_result = loop_content
            for key, value in item_context.items():
                if isinstance(value, str):
                    item_result = item_result.replace("{{ " + key + " }}", value)
            result.append(item_result)
        return "\n".join(result)

    content = re.sub(for_pattern, replace_for, content, flags=re.DOTALL)

    # Handle simple variable replacements
    for key, value in context.items():
        if isinstance(value, (str, int, float)):
            content = content.replace("{{ " + key + " }}", str(value))

    return content


def parse_outlook_date(date_str: str) -> datetime.datetime:
    """Parse Outlook date string to datetime object"""
    try:
        # Try ISO format first (YYYY-MM-DD HH:MM:SS)
        return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Try other common formats
            return datetime.datetime.strptime(date_str.strip(), "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            # Return current time if parsing fails
            logger.warning(f"Failed to parse date: {date_str}")
            return datetime.datetime.now()


def parse_email_csv(csv_data: str) -> list[Email]:
    """Parse CSV data into Email objects"""
    emails = []

    # Skip error messages
    if csv_data.startswith("ERROR:"):
        logger.error(csv_data)
        return emails

    reader = csv.DictReader(StringIO(csv_data))
    for row in reader:
        try:
            email = Email(
                identifier=row.get("identifier", ""),
                subject=row.get("subject", ""),
                sender_name=row.get("sender_name", ""),
                sender_email=row.get("sender_email", ""),
                to=row.get("to", ""),
                cc=row.get("cc", ""),
                received_at=parse_outlook_date(row.get("received_at", "")),
            )
            emails.append(email)
        except Exception as e:
            logger.warning(f"Failed to parse email row: {e}")
            continue

    return emails


def parse_email_detail(detail_str: str) -> Email:
    """Parse email detail string into Email object"""
    if detail_str.startswith("ERROR:"):
        raise ValueError(detail_str)

    # Parse structured output
    lines = detail_str.split("\n")
    data = {}
    body_lines = []
    in_body = False
    attachments = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if line == "=== BODY START ===":
            in_body = True
            i += 1
            continue
        elif line == "=== BODY END ===":
            in_body = False
            data["body"] = "\n".join(body_lines)
            i += 1
            continue
        elif in_body:
            body_lines.append(line)
            i += 1
            continue

        if ": " in line and not in_body:
            key, value = line.split(": ", 1)
            data[key] = value

        # Handle attachments
        if line == "=== ATTACHMENTS ===":
            i += 1
            while i < len(lines) and lines[i].startswith("filename: "):
                filename = lines[i].split(": ", 1)[1]
                i += 1
                if i < len(lines) and lines[i].startswith("size: "):
                    i += 1  # Skip size for now
                attachments.append(EmailAttachment(filename=filename, content_base64=""))

        i += 1

    return Email(
        identifier=data.get("identifier", ""),
        subject=data.get("subject", ""),
        sender_name=data.get("sender_name", ""),
        sender_email=data.get("sender_email", ""),
        to=data.get("to", ""),
        cc=data.get("cc", ""),
        received_at=parse_outlook_date(data.get("received_at", "")),
        body=data.get("body", ""),
        attachments=attachments,
    )


def get_folders(connection: Optional[Any] = None) -> list[OutlookFolderInfo]:
    """Get list of Outlook folders

    Args:
        connection: Ignored for macOS

    Returns:
        List of folder information
    """
    script = """
    tell application "Microsoft Outlook"
        set resultStr to ""
        repeat with aFolder in mail folders
            set folderName to name of aFolder
            set resultStr to resultStr & id of aFolder & "|" & folderName & return
        end repeat
        return resultStr
    end tell
    """

    try:
        stdout_str = applescript_run_sync(script).strip()

        folders = []
        for line in stdout_str.splitlines():
            if "|" in line:
                id_, name = line.split("|", 1)
                folders.append(
                    OutlookFolderInfo(
                        name=name.strip(),
                        entry_id=id_.strip(),
                    )
                )

        return folders
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        return []


def get_entry_id(
    folder_name: str,
    connection: Optional[Any] = None,
) -> str:
    """Get folder entry ID by name

    Args:
        folder_name: Name of the folder
        connection: Ignored for macOS

    Returns:
        Folder entry ID

    Raises:
        ValueError: If folder not found
    """
    for folder in get_folders(connection):
        if folder.name.lower() == folder_name.lower():
            return folder.entry_id
    raise ValueError(f"Folder '{folder_name}' not found.")


def get_emails(
    max_hours: int,
    query: Optional[str] = None,
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
    connection: Optional[Any] = None,
) -> list[Email]:
    """Get emails from Outlook

    Args:
        max_hours: Maximum hours to look back
        query: Search query for subject
        email_folder_type: Type of email folder
        email_folder_name: Name of email folder
        connection: Ignored for macOS

    Returns:
        List of emails
    """
    # Load and render template
    template_path = Path(__file__).parent / "templates" / "get_emails.applescript"

    context = {
        "max_hours": max_hours,
        "query": escape_applescript_string(query) if query else None,
        "folder_type": email_folder_type.value if email_folder_type else None,
        "folder_name": escape_applescript_string(email_folder_name) if email_folder_name else None,
    }

    script = render_template(template_path, context)

    try:
        result = applescript_run_sync(script)
        return parse_email_csv(result)
    except Exception as e:
        logger.error(f"Failed to get emails: {e}")
        return []


def get_email(
    identifier: str,
    connection: Optional[Any] = None,
) -> Email:
    """Get email details

    Args:
        identifier: Email ID
        connection: Ignored for macOS

    Returns:
        Email object with full details
    """
    # Load and render template
    template_path = Path(__file__).parent / "templates" / "get_email_detail.applescript"

    context = {
        "email_id": identifier,
    }

    script = render_template(template_path, context)

    try:
        result = applescript_run_sync(script)
        return parse_email_detail(result)
    except Exception as e:
        logger.error(f"Failed to get email details: {e}")
        raise


def send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: Union[str, list[str]],
    html_message: Optional[str] = None,
    cc_list: Optional[Union[str, list[str]]] = None,
    bcc_list: Optional[Union[str, list[str]]] = None,
    connection: Optional[Any] = None,
    force_sync: bool = True,
    compose_only: bool = False,
) -> str:
    """Send email via Outlook

    Args:
        subject: Email subject
        message: Email body (plain text)
        from_email: Sender email address
        recipient_list: Recipient emails (comma-separated string or list)
        html_message: HTML message (currently ignored on macOS)
        cc_list: CC recipients (comma-separated string or list)
        bcc_list: BCC recipients (comma-separated string or list)
        connection: Ignored for macOS
        force_sync: Ignored for macOS
        compose_only: If True, opens compose window without sending

    Returns:
        String describing the result of the operation
    """
    # Parse email lists
    recipient_list = parse_email_list(recipient_list)
    cc_list = parse_email_list(cc_list)
    bcc_list = parse_email_list(bcc_list)

    # Load and render template
    template_path = Path(__file__).parent / "templates" / "send_email.applescript"

    # For now, use plain message even if HTML is provided
    # TODO: Implement HTML email support
    if html_message and not message:
        # Convert HTML to plain text if only HTML is provided
        message = html_message

    context = {
        "subject": escape_applescript_string(subject),
        "message": escape_applescript_string(message),
        "from_email": from_email,
        "recipients": recipient_list,
        "cc_list": cc_list or [],
        "bcc_list": bcc_list or [],
        "attachments": [],  # TODO: Implement attachment support
        "compose_only": compose_only,
    }

    script = render_template(template_path, context)

    try:
        result = applescript_run_sync(script)
        if "SUCCESS" in result:
            if compose_only:
                return "Email compose window opened successfully in Outlook. The email is ready for review and manual sending."
            else:
                return "Email sent successfully via Outlook."
        else:
            error_msg = result.replace("ERROR: ", "") if "ERROR:" in result else result
            return f"Failed to {'open compose window' if compose_only else 'send email'} in Outlook: {error_msg}"
    except Exception as e:
        logger.error(f"Failed to {'open compose window' if compose_only else 'send email'}: {e}")
        return f"Failed to {'open compose window' if compose_only else 'send email'} in Outlook: {str(e)}"


def get_account_for_email_address(
    smtp_address: str,
    connection: Optional[Any] = None,
) -> Any:
    """Compatibility function - not used on macOS

    Account selection is handled in the AppleScript template
    """
    return None

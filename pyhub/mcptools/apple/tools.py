"""Apple MCP tools."""

from typing import Literal, Optional

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.apple import contacts, mail, messages, notes
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.core.email_types import Email, EmailFolderType
from pyhub.mcptools.core.json_utils import json_dumps

ENABLED_APPLE_TOOLS = OS.current_is_macos() and settings.USE_APPLE_TOOLS


@mcp.tool(enabled=ENABLED_APPLE_TOOLS)
async def apple_mail(
    operation: Literal["send", "list"] = Field(description="Operation to perform: send or list"),
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
    # List operation parameters
    max_hours: int = Field(default=24, description="Maximum number of hours to look back for emails"),
    query: Optional[str] = Field(default=None, description="Optional search query to filter emails"),
    folder: str = Field(
        default="inbox", description="Email folder to list (inbox, sent, drafts, trash, or custom folder name)"
    ),
) -> str:
    """Interact with Apple Mail app.

    Operations:
    - send: Send an email (or open compose window)
    - list: List emails from a specific folder

    Returns:
        JSON string with operation results
    """
    if operation == "send":
        # Validate required fields for send operation
        if not subject or not message or not from_email or not recipient_list:
            return json_dumps(
                {"error": "subject, message, from_email, and recipient_list are required for send operation"}
            )

        send_status_message = await mail.send_email(
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

    elif operation == "list":
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

    else:
        return json_dumps({"error": f"Unknown operation: {operation}"})


# Messages Tools
@mcp.tool(enabled=ENABLED_APPLE_TOOLS)
async def apple_messages(
    operation: Literal["send", "schedule", "unread"] = Field(
        description="Operation to perform: send, schedule, or unread"
    ),
    phone_number: Optional[str] = Field(default=None, description="Phone number for send operations"),
    message: Optional[str] = Field(default=None, description="Message content for send operation"),
    scheduled_time: Optional[str] = Field(default=None, description="ISO format datetime for scheduled messages"),
    service: Literal["iMessage", "SMS"] = Field(default="iMessage", description="Service to use for sending messages"),
) -> str:
    """Interact with Apple Messages app.

    Note: Due to macOS privacy restrictions, reading message content is not supported.

    Operations:
    - send: Send a message to a phone number
    - schedule: Schedule a message for future delivery (creates a reminder)
      WARNING: Due to timezone differences between macOS and iOS Reminders app,
      scheduled times may display differently on each device.
    - unread: Get count of unread messages

    Returns:
        JSON string with operation results
    """
    if operation == "send":
        if not phone_number or not message:
            return json_dumps({"error": "phone_number and message are required for send operation"})
        result = await messages.send_message(phone_number, message, service)
        return json_dumps(result)

    elif operation == "schedule":
        if not phone_number or not message or not scheduled_time:
            return json_dumps(
                {"error": "phone_number, message, and scheduled_time are required for schedule operation"}
            )
        client = messages.MessagesClient()
        result = await client.schedule_message(phone_number, message, scheduled_time)
        return json_dumps(result)

    elif operation == "unread":
        count = await messages.get_unread_count()
        return json_dumps({"unread_count": count})

    else:
        return json_dumps({"error": f"Unknown operation: {operation}"})


# Notes Tools
@mcp.tool(enabled=ENABLED_APPLE_TOOLS)
async def apple_notes(
    operation: Literal["list", "search", "create", "get", "folders"] = Field(
        description="Operation to perform: list, search, create, get, or folders"
    ),
    search_text: Optional[str] = Field(default=None, description="Text to search for in notes"),
    title: Optional[str] = Field(default=None, description="Note title for create operation"),
    body: Optional[str] = Field(default=None, description="Note content for create operation"),
    folder_name: Optional[str] = Field(default=None, description="Folder name to filter or create notes in"),
    note_id: Optional[str] = Field(default=None, description="Note ID for get operation"),
    limit: int = Field(default=20, description="Maximum number of notes to return"),
) -> str:
    """Search, retrieve and create notes in Apple Notes app.

    Operations:
    - list: List notes (optionally filtered by folder)
    - search: Search notes by text content
    - create: Create a new note
    - get: Get a specific note by ID
    - folders: List all folders

    Returns:
        JSON string with operation results
    """
    if operation == "list":
        result = await notes.list_notes(folder_name, limit)
        return json_dumps(result)

    elif operation == "search":
        if not search_text:
            return json_dumps({"error": "search_text is required for search operation"})
        result = await notes.search_notes(search_text, folder_name, limit)
        return json_dumps(result)

    elif operation == "create":
        if not title or not body:
            return json_dumps({"error": "title and body are required for create operation"})
        result = await notes.create_note(title, body, folder_name)
        return json_dumps(result)

    elif operation == "get":
        if not note_id:
            return json_dumps({"error": "note_id is required for get operation"})
        result = await notes.get_note(note_id)
        if result:
            return json_dumps(result)
        else:
            return json_dumps({"error": "Note not found"})

    elif operation == "folders":
        result = await notes.list_folders()
        return json_dumps({"folders": result})

    else:
        return json_dumps({"error": f"Unknown operation: {operation}"})


# Contacts Tools
@mcp.tool(enabled=ENABLED_APPLE_TOOLS)
async def apple_contacts(
    operation: Literal["search", "get", "create"] = Field(description="Operation to perform: search, get, or create"),
    name: Optional[str] = Field(default=None, description="Name to search for (partial match)"),
    email: Optional[str] = Field(default=None, description="Email address to search for or add"),
    phone: Optional[str] = Field(default=None, description="Phone number to search for or add"),
    contact_id: Optional[str] = Field(default=None, description="Contact ID for get operation"),
    first_name: Optional[str] = Field(default=None, description="First name for create operation"),
    last_name: Optional[str] = Field(default=None, description="Last name for create operation"),
    organization: Optional[str] = Field(default=None, description="Organization/company for create operation"),
    note: Optional[str] = Field(default=None, description="Additional notes for create operation"),
    limit: int = Field(default=20, description="Maximum number of contacts to return for search"),
) -> str:
    """Search and retrieve contacts from Apple Contacts app.

    Operations:
    - search: Search contacts by name, email, or phone
    - get: Get a specific contact by ID
    - create: Create a new contact

    Returns:
        JSON string with operation results
    """
    if operation == "search":
        result = await contacts.search_contacts(name, email, phone, limit)
        return json_dumps(result)

    elif operation == "get":
        if not contact_id:
            return json_dumps({"error": "contact_id is required for get operation"})
        result = await contacts.get_contact(contact_id)
        if result:
            return json_dumps(result)
        else:
            return json_dumps({"error": "Contact not found"})

    elif operation == "create":
        if not first_name:
            return json_dumps({"error": "first_name is required for create operation"})
        result = await contacts.create_contact(first_name, last_name, email, phone, organization, note)
        return json_dumps(result)

    else:
        return json_dumps({"error": f"Unknown operation: {operation}"})

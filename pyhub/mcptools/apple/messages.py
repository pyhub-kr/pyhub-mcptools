"""Apple Messages integration."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import time
import json

from pyhub.mcptools.apple.utils import (
    applescript_run,
    escape_applescript_string,
    parse_applescript_list,
    parse_applescript_record,
    format_phone_number,
    activate_app,
)


class MessagesClient:
    """Client for interacting with Apple Messages app.

    Note: Due to macOS privacy restrictions, reading message content is not supported.
    Apple's Messages app does not allow AppleScript access to message history.
    Only sending messages, scheduling (via Reminders), and checking unread count are available.
    """

    async def send_message(
        self,
        phone_number: str,
        message: str,
        service: str = "iMessage"
    ) -> Dict[str, Any]:
        """Send a message via Messages app.

        Args:
            phone_number: Recipient's phone number
            message: Message content
            service: Service to use ("iMessage" or "SMS")

        Returns:
            Dictionary with status and details
        """
        formatted_phone = format_phone_number(phone_number)
        escaped_message = escape_applescript_string(message)

        script = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = {service}
            set targetBuddy to participant "{formatted_phone}" of targetService
            send "{escaped_message}" to targetBuddy
            return "SUCCESS"
        end tell
        '''

        try:
            result = await applescript_run(script)
            return {
                "status": "success",
                "phone_number": phone_number,
                "message": message,
                "service": service,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "phone_number": phone_number
            }

    # Note: read_messages functionality is not implemented due to macOS privacy restrictions.
    # Apple's Messages app does not allow AppleScript access to message content or chat history
    # for security reasons. Only sending messages and checking unread count are supported.

    async def schedule_message(
        self,
        phone_number: str,
        message: str,
        scheduled_time: str
    ) -> Dict[str, Any]:
        """Schedule a message for future delivery.

        Note: This creates a reminder to send the message, as Messages app
        doesn't have native scheduling support.

        Args:
            phone_number: Recipient's phone number
            message: Message content
            scheduled_time: When to send (ISO format)

        Returns:
            Dictionary with scheduling details
        """
        # Parse the scheduled time
        try:
            dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            # Keep the original datetime with timezone info
            # This preserves the user's intended time regardless of system timezone

            # Use the datetime as-is to maintain consistency across devices
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            minute = dt.minute

            # Also prepare a human-readable version for the reminder body
            if dt.tzinfo is not None:
                local_dt = dt.astimezone()
                time_str = local_dt.strftime("%Y-%m-%d %H:%M %Z")
            else:
                time_str = dt.strftime("%Y-%m-%d %H:%M")

        except Exception as e:
            return {
                "status": "error",
                "error": f"Invalid scheduled_time format. Use ISO format. Error: {str(e)}"
            }

        escaped_message = escape_applescript_string(message)
        reminder_title = f"Send message to {phone_number}"
        reminder_body = f"Message: {escaped_message}\nScheduled for: {time_str}"

        # Create reminder with explicit date components
        script = f'''
        tell application "Reminders"
            -- Create date with explicit components
            set reminderDate to current date
            set year of reminderDate to {year}
            set month of reminderDate to {month}
            set day of reminderDate to {day}
            set hours of reminderDate to {hour}
            set minutes of reminderDate to {minute}
            set seconds of reminderDate to 0

            set newReminder to make new reminder with properties {{name:"{escape_applescript_string(reminder_title)}", body:"{escape_applescript_string(reminder_body)}", remind me date:reminderDate}}
            return "SUCCESS"
        end tell
        '''

        try:
            result = await applescript_run(script)
            return {
                "status": "scheduled",
                "phone_number": phone_number,
                "message": message,
                "scheduled_time": scheduled_time,
                "reminder_created": True,
                "warning": "Due to timezone handling differences between macOS and iOS Reminders app, the scheduled time may appear differently on each device. Please verify the reminder time in your Reminders app before the scheduled time."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_unread_count(self) -> int:
        """Get count of unread messages."""
        script = '''
        tell application "Messages"
            set unreadCount to 0
            try
                repeat with theChat in chats
                    set theMessages to messages of theChat
                    repeat with theMessage in theMessages
                        try
                            set isRead to read of theMessage
                            set isFromMe to (sender of theMessage is missing value)
                            if isRead is false and isFromMe is false then
                                set unreadCount to unreadCount + 1
                            end if
                        end try
                    end repeat
                end repeat
            end try
            return unreadCount
        end tell
        '''

        result = await applescript_run(script)
        try:
            return int(result.strip())
        except:
            return 0


# Convenience functions
async def send_message(phone_number: str, message: str, service: str = "iMessage") -> Dict[str, Any]:
    """Send a message via Messages app."""
    client = MessagesClient()
    return await client.send_message(phone_number, message, service)


async def get_unread_count() -> int:
    """Get count of unread messages."""
    client = MessagesClient()
    return await client.get_unread_count()
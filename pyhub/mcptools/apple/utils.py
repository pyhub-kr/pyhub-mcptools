"""Common utilities for Apple integrations."""

from typing import Optional, Dict, Any
import re
from pyhub.mcptools.microsoft.excel.utils import applescript_run


def escape_applescript_string(text: str) -> str:
    """Escape special characters for AppleScript strings."""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


def parse_applescript_list(output: str, delimiter: str = "|||") -> list[str]:
    """Parse AppleScript list output into Python list."""
    if not output or output == "missing value":
        return []
    return [item.strip() for item in output.split(delimiter) if item.strip()]


def parse_applescript_record(output: str, field_delimiter: str = "|||", kv_delimiter: str = ":::") -> Dict[str, str]:
    """Parse AppleScript record output into Python dictionary."""
    result = {}
    if not output or output == "missing value":
        return result

    for field in output.split(field_delimiter):
        if kv_delimiter in field:
            key, value = field.split(kv_delimiter, 1)
            result[key.strip()] = value.strip()

    return result


def build_date_filter_script(days_back: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Build AppleScript date filter conditions."""
    if days_back:
        return f"set thresholdDate to (current date) - ({days_back} * days)"
    elif start_date and end_date:
        return f"""
        set startDate to date "{start_date}"
        set endDate to date "{end_date}"
        """
    elif start_date:
        return f'set startDate to date "{start_date}"'
    else:
        return ""


async def check_app_running(app_name: str) -> bool:
    """Check if an application is running."""
    script = f'''
    tell application "System Events"
        set appRunning to (name of processes) contains "{app_name}"
    end tell
    return appRunning
    '''
    result = await applescript_run(script)
    return result.strip().lower() == "true"


async def activate_app(app_name: str) -> None:
    """Activate (bring to front) an application."""
    script = f'tell application "{app_name}" to activate'
    await applescript_run(script)


def format_phone_number(phone: str) -> str:
    """Format phone number for Messages app."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Add country code if missing (assuming US)
    if len(digits) == 10:
        digits = '1' + digits

    return digits
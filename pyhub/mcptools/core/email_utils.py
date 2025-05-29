"""Email utility functions."""

from typing import Union


def parse_email_list(emails: Union[str, list[str], None]) -> list[str]:
    """Convert email string or list to normalized list.

    Args:
        emails: Can be:
            - None: returns empty list
            - str: comma-separated email addresses
            - list[str]: returns as-is

    Returns:
        List of email addresses with whitespace trimmed
    """
    if emails is None:
        return []

    if isinstance(emails, str):
        # Split by comma and strip whitespace
        return [email.strip() for email in emails.split(",") if email.strip()]

    # Already a list
    return emails

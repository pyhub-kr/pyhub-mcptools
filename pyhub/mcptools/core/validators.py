"""Common validators for spreadsheet operations."""

import re
from functools import wraps
from typing import Callable

from pyhub.mcptools.google.sheets.exceptions import GoogleSheetsError
from pyhub.mcptools.microsoft.excel.exceptions import DataValidationError

# Regex patterns for validation
SPREADSHEET_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{20,}$")
EXCEL_RANGE_PATTERN = re.compile(r"^(?:([^!]+)!)?([A-Z]+\d+(?::[A-Z]+\d+)?|[A-Z]+:[A-Z]+|\d+:\d+)$", re.IGNORECASE)
GOOGLE_RANGE_PATTERN = re.compile(r"^(?:([^!]+)!)?([A-Z]+\d*(?::[A-Z]+\d*)?|[A-Z]+:[A-Z]+|\d+:\d+)$", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_spreadsheet_id(func: Callable) -> Callable:
    """Validate Google Sheets spreadsheet ID format."""
    import inspect

    @wraps(func)
    async def wrapper(*args, **kwargs):
        spreadsheet_id = kwargs.get("spreadsheet_id") or (args[0] if args else None)

        if not spreadsheet_id:
            raise GoogleSheetsError("Spreadsheet ID is required")

        if not isinstance(spreadsheet_id, str):
            raise GoogleSheetsError(f"Spreadsheet ID must be a string, got {type(spreadsheet_id).__name__}")

        if not SPREADSHEET_ID_PATTERN.match(spreadsheet_id):
            raise GoogleSheetsError(
                f"Invalid spreadsheet ID format: '{spreadsheet_id}'. " f"Please provide a valid Google Sheets ID."
            )

        # 함수가 비동기인지 확인하고 적절히 호출
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper


def validate_range_format(func: Callable) -> Callable:
    """Validate spreadsheet range format (works for both Excel and Google Sheets)."""
    import inspect

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Try to find range parameter in various names
        range_param = None
        range_name = None

        for param_name in ["sheet_range", "range", "cell_range"]:
            if param_name in kwargs:
                range_param = kwargs[param_name]
                range_name = param_name
                break

        # If not in kwargs, check positional args (usually second arg after spreadsheet_id)
        if range_param is None and len(args) > 1:
            range_param = args[1]
            range_name = "range"

        # Skip validation if range is optional and not provided
        if not range_param:
            # 함수가 비동기인지 확인하고 적절히 호출
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        if not isinstance(range_param, str):
            raise DataValidationError(range_name, range_param, "string in format 'A1:B10' or 'Sheet1!A1:B10'")

        # Determine if this is for Excel or Google Sheets based on function name
        is_excel = "excel" in func.__name__
        pattern = EXCEL_RANGE_PATTERN if is_excel else GOOGLE_RANGE_PATTERN

        if not pattern.match(range_param):
            raise DataValidationError(
                range_name, range_param, "valid range format like 'A1:B10', 'Sheet1!A1:B10', 'A:E', or '1:5'"
            )

        # 함수가 비동기인지 확인하고 적절히 호출
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper


def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        raise ValueError("이메일 주소가 필요합니다")

    if not EMAIL_PATTERN.match(email.strip()):
        raise ValueError(f"유효하지 않은 이메일 주소 형식: {email}")

    return True


def validate_csv_data(func: Callable) -> Callable:
    """Validate CSV data format."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        csv_data = kwargs.get("values") or kwargs.get("data")

        if csv_data and isinstance(csv_data, str):
            # Basic CSV validation - check for suspicious patterns
            if "\x00" in csv_data:
                raise DataValidationError("csv_data", "contains null bytes", "valid CSV string without null bytes")

            # Check for reasonable size (prevent memory issues)
            if len(csv_data) > 10 * 1024 * 1024:  # 10MB limit
                raise DataValidationError("csv_data", f"{len(csv_data)} bytes", "CSV data under 10MB")

        return await func(*args, **kwargs)

    return wrapper


def validate_workbook_name(func: Callable) -> Callable:
    """Validate Excel workbook name."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        book_name = kwargs.get("book_name") or kwargs.get("workbook_name")

        if book_name and not isinstance(book_name, str):
            raise DataValidationError("book_name", book_name, "string containing workbook name")

        # Check for invalid characters in filename
        if book_name and any(char in book_name for char in '<>:"|?*'):
            raise DataValidationError(
                "book_name", book_name, 'valid filename without special characters: < > : " | ? *'
            )

        return await func(*args, **kwargs)

    return wrapper


def validate_sheet_name(func: Callable) -> Callable:
    """Validate sheet name."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        sheet_name = kwargs.get("sheet_name")

        if sheet_name and not isinstance(sheet_name, str):
            raise DataValidationError("sheet_name", sheet_name, "string containing sheet name")

        # Excel sheet name restrictions
        if sheet_name and "excel" in func.__name__:
            if len(sheet_name) > 31:
                raise DataValidationError(
                    "sheet_name", f"{len(sheet_name)} characters", "sheet name with 31 or fewer characters"
                )

            invalid_chars = ["\\", "/", "?", "*", "[", "]", ":"]
            if any(char in sheet_name for char in invalid_chars):
                raise DataValidationError(
                    "sheet_name", sheet_name, f'sheet name without invalid characters: {", ".join(invalid_chars)}'
                )

        return await func(*args, **kwargs)

    return wrapper


def validate_positive_integer(param_name: str) -> Callable:
    """Validate that a parameter is a positive integer."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            value = kwargs.get(param_name)

            if value is not None:
                if not isinstance(value, int) or value <= 0:
                    raise DataValidationError(param_name, value, "positive integer greater than 0")

            return await func(*args, **kwargs)

        return wrapper

    return decorator

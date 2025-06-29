"""Utility functions for Google Sheets operations."""

import json
from typing import Any, Union


def json_dumps(data: Any) -> str:
    """Serialize data to JSON string with proper formatting."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def resolve_field_value(value: Any) -> Any:
    """Resolve pydantic Field object to its actual value.

    This is needed because when using Field(default=...) in function parameters,
    the parameter might be a FieldInfo object instead of the actual value,
    which causes JSON serialization errors.
    """
    from pydantic.fields import FieldInfo

    if isinstance(value, FieldInfo):
        return value.default
    return value


def parse_sheet_range(sheet_range: str) -> tuple[str, str]:
    """Parse sheet range into sheet name and cell range.

    Args:
        sheet_range: Range string like "Sheet1!A1:B10" or "A1:B10"

    Returns:
        Tuple of (sheet_name, range_str)
    """
    if "!" in sheet_range:
        parts = sheet_range.split("!", 1)
        return parts[0], parts[1]
    else:
        # If no sheet name specified, return empty string for sheet name
        return "", sheet_range


def ensure_2d_array(values: Union[list[Any], list[list[Any]]]) -> list[list[Any]]:
    """Ensure values is a 2D array.

    Args:
        values: Single value, 1D array, or 2D array

    Returns:
        2D array
    """
    if not values:
        return [[]]

    # If it's not a list, make it a 2D array with single cell
    if not isinstance(values, list):
        return [[values]]

    # If it's empty list, return empty 2D array
    if len(values) == 0:
        return [[]]

    # If first element is not a list, it's a 1D array
    if not isinstance(values[0], list):
        return [values]

    # Already a 2D array
    return values


def convert_a1_to_coordinates(a1_notation: str) -> tuple[int, int]:
    """Convert A1 notation to zero-based row and column coordinates.

    Args:
        a1_notation: Cell reference like "A1", "B10", "AA25"

    Returns:
        Tuple of (row, col) zero-based indices
    """
    import re

    match = re.match(r"^([A-Z]+)(\d+)$", a1_notation.upper())
    if not match:
        raise ValueError(f"Invalid A1 notation: {a1_notation}")

    col_str, row_str = match.groups()

    # Convert column letters to number (A=0, B=1, ..., Z=25, AA=26, ...)
    col = 0
    for i, char in enumerate(reversed(col_str)):
        col += (ord(char) - ord("A") + 1) * (26**i)
    col -= 1  # Zero-based

    # Convert row to zero-based
    row = int(row_str) - 1

    return row, col


def convert_coordinates_to_a1(row: int, col: int) -> str:
    """Convert zero-based row and column coordinates to A1 notation.

    Args:
        row: Zero-based row index
        col: Zero-based column index

    Returns:
        A1 notation string
    """
    # Convert column number to letters
    col_str = ""
    col += 1  # Make it 1-based for calculation

    while col > 0:
        col -= 1
        col_str = chr(ord("A") + col % 26) + col_str
        col //= 26

    return f"{col_str}{row + 1}"


def parse_csv_data(csv_string: str) -> list[list[str]]:
    """Parse CSV string into 2D array.

    Args:
        csv_string: CSV formatted string

    Returns:
        2D array of values
    """
    import csv
    from io import StringIO

    # Handle empty string
    if not csv_string:
        return [[]]

    # Parse CSV
    reader = csv.reader(StringIO(csv_string))
    return list(reader)

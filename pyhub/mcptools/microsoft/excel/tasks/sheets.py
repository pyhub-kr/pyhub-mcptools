"""Minimal sheets tasks file - only contains functions still used by delegator pattern."""

from pathlib import Path

import xlwings as xw
from pydantic import Field

from pyhub.mcptools.microsoft.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.microsoft.excel.types import ExcelExpandMode, ExcelGetValueType
from pyhub.mcptools.microsoft.excel.utils import (
    convert_to_csv,
    csv_loads,
    fix_data,
    get_range,
    get_sheet,
    json_dumps,
    json_loads,
    normalize_text,
)
from pyhub.mcptools.fs.utils import validate_path


@macos_excel_request_permission
def get_opened_workbooks() -> str:
    """Get a list of all open workbooks and their sheets in Excel

    Returns:
        str: JSON string containing:
            - books: List of open workbooks
                - name: Workbook name
                - fullname: Full path of workbook
                - sheets: List of sheets in workbook
                    - name: Sheet name
                    - index: Sheet index
                    - range: Used range address (e.g. "$A$1:$E$665")
                    - count: Total number of cells in used range
                    - shape: Tuple of (rows, columns) in used range
                    - active: Whether this is the active sheet
                - active: Whether this is the active workbook
    """

    return json_dumps(
        {
            "books": [
                {
                    "name": normalize_text(book.name),
                    "fullname": normalize_text(book.fullname),
                    "sheets": [
                        {
                            "name": normalize_text(sheet.name),
                            "index": sheet.index,
                            "range": sheet.used_range.get_address(),  # "$A$1:$E$665"
                            "count": sheet.used_range.count,  # 3325 (total number of cells)
                            "shape": sheet.used_range.shape,  # (655, 5)
                            "active": sheet == xw.sheets.active,
                            "table_names": [table.name for table in sheet.tables],
                        }
                        for sheet in book.sheets
                    ],
                    "active": book == xw.books.active,
                }
                for book in xw.books
            ]
        }
    )


@macos_excel_request_permission
def get_values(
    sheet_range: str = Field(
        default="",
        description="""Excel range to get data. If not specified, uses the entire used range of the sheet.
            Important: When using expand_mode, specify ONLY the starting cell (e.g., 'A1' not 'A1:B10')
            as the range will be automatically expanded.""",
        examples=["A1", "Sheet1!A1", "A1:C10"],
    ),
    book_name: str = Field(
        default="",
        description="Name of workbook to use. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: str = Field(
        default="",
        description="Name of sheet to use. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
    expand_mode: str = Field(
        default=ExcelExpandMode.get_none_value(),
        description=ExcelExpandMode.get_description(
            "Mode for automatically expanding the selection range. "
            "All expand modes only work in the right/down direction"
        ),
    ),
    value_type: str = Field(
        default=ExcelGetValueType.get_none_value(),
        description=ExcelGetValueType.get_description("Type of data to retrieve"),
    ),
) -> str:
    """Read data from a specified range in an Excel workbook

    Retrieves data with options for range expansion and output format.
    Uses active workbook/sheet if not specified.

    Returns:
        str: CSV format by default. Use value_type to change output format.

    Examples:
        >>> get_values("A1:C10")  # Basic range
        >>> get_values("A1", expand_mode="table")  # Auto-expand from A1
        >>> get_values("Sheet1!B2:D5", value_type="json")  # JSON output
        >>> get_values("", book_name="Sales.xlsx")  # Entire used range
    """

    range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )

    values = range_.value

    # Process according to value_type
    if value_type == ExcelGetValueType.FORMULA2.value:
        # Return formulas instead of values
        values = range_.formula2
        return json_dumps(values)
    else:
        # Default: VALUES - return as CSV format
        if values is None:
            return ""
        elif not isinstance(values, list):
            # Single cell
            return str(values)
        elif values and not isinstance(values[0], list):
            # Single row/column
            return convert_to_csv([values])
        else:
            # Multiple rows/columns
            return convert_to_csv(values)


@macos_excel_request_permission
def set_values(
    sheet_range: str = Field(
        description="Excel cell range to write data to",
        examples=["A1", "A1:D10", "B:E", "3:7", "Sheet1!A1:D10"],
    ),
    values: str = Field(
        default=None,
        description="CSV string. Values containing commas must be enclosed in double quotes (e.g. 'a,\"b,c\",d')",
    ),
    csv_abs_path: str = Field(
        default="",
        description="""Absolute path to the CSV file to read.
            If specified, this will override any value provided in the 'values' parameter.
            Either 'csv_abs_path' or 'values' must be provided, but not both.""",
        examples=["/path/to/data.csv"],
    ),
    book_name: str = Field(
        default="",
        description="Name of workbook to use. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: str = Field(
        default="",
        description="Name of sheet to use. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
) -> str:
    """Write data to a specified range in an Excel workbook.

    Performance Tips:
        - When setting values to multiple consecutive cells, it's more efficient to use a single call
          with a range (e.g. "A1:B10") rather than making multiple calls for individual cells.
        - For large datasets, using CSV format with range notation is significantly faster than
          making separate calls for each cell.

    Returns:
        str: Success message indicating values were set.

    Examples:
        >>> set_values(sheet_range="A1", values="v1,v2,v3\\nv4,v5,v6")  # grid using CSV
        >>> set_values(sheet_range="A1:B3", values="1,2\\n3,4\\n5,6")  # faster than 6 separate calls
        >>> set_values(sheet_range="Sheet1!A1:C2", values="[[1,2,3],[4,5,6]]")  # using JSON array
        >>> set_values(csv_abs_path="/path/to/data.csv", sheet_range="A1")  # import from CSV file
    """

    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

    if csv_abs_path:
        csv_path: Path = validate_path(csv_abs_path)
        with csv_path.open("rt", encoding="utf-8") as f:
            values = f.read()

    if values is not None:
        if values.strip().startswith(("[", "{")):
            data = json_loads(values)
        else:
            data = csv_loads(values)
    else:
        raise ValueError("Either csv_abs_path or values must be provided.")

    range_.value = fix_data(sheet_range, data)

    return f"Successfully set values to {range_.address}."

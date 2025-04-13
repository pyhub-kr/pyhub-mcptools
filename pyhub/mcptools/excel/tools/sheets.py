"""
Excel automation
"""

import csv
import json
from typing import Optional, Union

import xlwings as xw
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import ExcelExpandMode, ExcelFormula, ExcelGetValuesResponse, ExcelRange
from pyhub.mcptools.excel.utils import (
    convert_to_csv,
    csv_loads,
    fix_data,
    get_range,
    json_dumps,
    json_loads,
    normalize_text,
)


@mcp.tool()
@macos_excel_request_permission
def excel_get_opened_workbooks() -> str:
    """Get a list of all open workbooks and their sheets in Excel"""

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
                        }
                        for sheet in book.sheets
                    ],
                    "active": book == xw.books.active,
                }
                for book in xw.books
            ]
        }
    )


@mcp.tool()
@macos_excel_request_permission
def excel_get_values(
    sheet_range: Optional[ExcelRange] = Field(
        default=None,
        description="Excel range to get data. If not specified, uses the entire used range of the sheet.",
        examples=["A1:C10", "Sheet1!A1:B5"],
    ),
    book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook to use. If not specified, uses the active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet to use. If not specified, uses the active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
    expand_mode: Optional[ExcelExpandMode] = Field(
        default=None,
        description="""Mode for automatically expanding the selection range. Supports:
            - "table": Expands only to the right and down from the starting cell
            - "right": Expands horizontally to include all contiguous data to the right
            - "down": Expands vertically to include all contiguous data below
            Note: All expand modes only work in the right/down direction from the starting cell.
                  No expansion occurs to the left or upward direction.
        """,
        examples=["table", "right", "down"],
    ),
) -> ExcelGetValuesResponse:
    """Get data from Excel workbook.

    Retrieves data from a specified Excel range. By default uses the active workbook and sheet
    if no specific book_name or sheet_name is provided.

    Returns:
        ExcelGetValuesResponse: A response model containing the data in CSV format.

    Examples:
        >>> excel_get_values("A1")  # Gets single cell value
        >>> excel_get_values("A1:B10")  # Gets range in CSV format
        >>> excel_get_values("A1", expand_mode="table")  # Gets table data in CSV
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

    if expand_mode is not None:
        range_ = range_.expand(mode=expand_mode.value.lower())

    data = range_.value

    if data is None:
        return ExcelGetValuesResponse(data="")

    # Convert single value to 2D list format
    if not isinstance(data, list):
        data = [[data]]
    elif data and not isinstance(data[0], list):
        data = [data]

    return ExcelGetValuesResponse(data=convert_to_csv(data))


@mcp.tool()
@macos_excel_request_permission
def excel_set_values(
    sheet_range: ExcelRange = Field(
        description="Excel range where to write the data",
        examples=["A1", "B2:B10", "Sheet1!A1:C5"],
    ),
    json_values: Union[str, list] = Field(
        description="""Data to write, either as:
        1. CSV string (recommended): "v1,v2,v3\\nv4,v5,v6"
        2. JSON string: '["v1", "v2", "v3"]'
        3. Python list: [["v1", "v2"], ["v3", "v4"]]""",
        examples=[
            "v1,v2,v3\nv4,v5,v6",  # CSV format
            '["v1", "v2", "v3"]',  # JSON format
            '[["v1"], ["v2"], ["v3"]]',
            '[["v1", "v2"], ["v3", "v4"]]',
        ],
    ),
    book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook to use. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet to use. If None, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
    autofit: bool = Field(
        default=False,
        description="If True, automatically adjusts the column widths to fit the content.",
    ),
) -> None:
    """Write data to a specified range in an Excel workbook.

    When adding values to consecutive cells, you only need to specify the starting cell coordinate,
    and the data will be populated according to the dimensions of the input.

    Input Format Priority (Recommended Order):
        1. CSV String (Recommended):
           - Most readable and natural format for tabular data
           - Example: "v1,v2,v3\\nv4,v5,v6"
           - Each line represents a row
           - Values separated by commas
           - Handles quoted values and escaping automatically
           - Uses Python's csv module for robust parsing

        2. JSON String/Python List:
           - Alternative format for programmatic use
           - Supports both flat and nested structures
           - More verbose but offers precise control over data structure

    Data Orientation Rules:
        For JSON/List format:
        - Flat list ["v1", "v2", "v3"] will always be written horizontally (row orientation)
        - Nested list [["v1"], ["v2"], ["v3"]] will be written vertically (column orientation)
        - For multiple rows/columns: [["v1", "v2"], ["v3", "v4"]] creates a 2x2 grid

    Range Format Rules:
        - For multiple columns (e.g., "A1:C1"), ensure data matches the range width
        - For multiple rows (e.g., "A1:A10"), ensure data matches the range height
        - Each row must have the same number of columns
        - Each column must have the same number of rows

    Returns:
        None

    Examples:
        # CSV format (recommended)
        >>> excel_set_values("A1", "v1,v2,v3\\nv4,v5,v6")  # 2x3 grid using CSV
        >>> excel_set_values("A1", "name,age\\nJohn,30\\nJane,25")  # Table with headers
        >>> excel_set_values("A1", '"Smith, John",age\\n"Doe, Jane",25')  # Handles commas in values

        # JSON/List format
        >>> excel_set_values("A1", '["v1", "v2", "v3"]')  # Write horizontally
        >>> excel_set_values("A1", '[["v1"], ["v2"], ["v3"]]')  # Write vertically
        >>> excel_set_values("A1", '[["v1", "v2"], ["v3", "v4"]]')  # Write 2x2 grid
        >>> excel_set_values("Sheet2!A1", '["v1", "v2"]', book_name="Sales.xlsx")  # Write to specific sheet
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

    # Try parsing as CSV first if the input is a string
    if isinstance(json_values, str):
        try:
            # First try CSV parsing
            data = csv_loads(json_values)
            range_.value = fix_data(sheet_range, data)
            if autofit:
                range_.autofit()
            return
        except (csv.Error, ValueError):
            # CSV 파싱 실패 시 JSON 파싱 시도
            try:
                data = json_loads(json_values)
            except json.JSONDecodeError as je:
                raise ValueError(f"Invalid input format. Expected CSV or JSON format. Error: {str(je)}") from je
    else:
        # If input is already a list, use it directly
        data = json_values

    range_.value = fix_data(sheet_range, data)
    if autofit:
        range_.autofit()


@mcp.tool()
@macos_excel_request_permission
def excel_autofit(
    sheet_range: ExcelRange = Field(
        description="Excel range to autofit",
        examples=["A1:D10", "A:E", "Sheet1!A:A"],
    ),
    book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook to use. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet to use. If None, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
    expand_mode: Optional[ExcelExpandMode] = Field(
        default=None,
        description="""Mode for automatically expanding the selection range. Options:
            - "table": Expands right and down from starting cell
            - "right": Expands horizontally to include contiguous data
            - "down": Expands vertically to include contiguous data""",
        examples=["table", "right", "down"],
    ),
) -> None:
    """Automatically adjusts column widths to fit the content in the specified Excel range.

    Makes all data visible without truncation by adjusting column widths. Uses the active workbook
    and sheet by default if no specific book_name or sheet_name is provided.

    Expand Mode Behavior:
        - All expand modes only work in the right/down direction
        - No expansion occurs to the left or upward direction
        - "table": Expands both right and down to include all contiguous data
        - "right": Expands only horizontally to include contiguous data
        - "down": Expands only vertically to include contiguous data

    Returns:
        None

    Examples:
        >>> excel_autofit("A1:D10")  # Autofit specific range
        >>> excel_autofit("A:E")  # Autofit entire columns A through E
        >>> excel_autofit("A:A", book_name="Sales.xlsx", sheet_name="Q1")  # Specific sheet
        >>> excel_autofit("A1", expand_mode="table")  # Autofit table data
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    if expand_mode is not None:
        range_ = range_.expand(mode=expand_mode.value.lower())
    range_.autofit()


@mcp.tool()
@macos_excel_request_permission
def excel_set_formula(
    sheet_range: ExcelRange = Field(
        description="Excel range where to apply the formula",
        examples=["A1", "B2:B10", "Sheet1!C1:C10"],
    ),
    formula: ExcelFormula = Field(
        description="Excel formula to set. Must start with '=' and follow Excel formula syntax.",
        examples=["=SUM(B1:B10)", "=A1*B1", "=VLOOKUP(A1, Sheet2!A:B, 2, FALSE)"],
    ),
    book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook to use. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet to use. If None, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
) -> None:
    """Set a formula in a specified range of an Excel workbook.

    Applies an Excel formula to the specified range using Excel's formula2 property,
    which supports modern Excel features and dynamic arrays. The formula will be
    evaluated by Excel after being set.

    Formula Behavior:
        - Must start with "=" and follow Excel formula syntax
        - Cell references are automatically adjusted for multiple cells
        - Supports array formulas (CSE formulas)
        - Uses modern dynamic array features via formula2 property

    Returns:
        None

    Examples:
        >>> excel_set_formula("A1", "=SUM(B1:B10)")  # Basic sum formula
        >>> excel_set_formula("C1:C10", "=A1*B1")  # Multiply columns
        >>> excel_set_formula("D1", "=VLOOKUP(A1, Sheet2!A:B, 2, FALSE)")  # Lookup
        >>> excel_set_formula("Sheet1!E1", "=AVERAGE(A1:D1)", book_name="Sales.xlsx")  # Average
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    range_.formula2 = formula


@mcp.tool()
@macos_excel_request_permission
def excel_add_sheet(
    name: Optional[str] = Field(
        default=None,
        description="Name of the new sheet. If None, Excel assigns a default name.",
        examples=["Sales2024", "Summary", "Data"],
    ),
    book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook to add sheet to. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    at_start: bool = Field(
        default=False,
        description="If True, adds the sheet at the beginning of the workbook.",
    ),
    at_end: bool = Field(
        default=False,
        description="If True, adds the sheet at the end of the workbook.",
    ),
    before_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of the sheet before which to insert the new sheet.",
        examples=["Sheet1", "Summary"],
    ),
    after_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of the sheet after which to insert the new sheet.",
        examples=["Sheet1", "Summary"],
    ),
) -> str:
    """Add a new sheet to an Excel workbook.

    Creates a new worksheet in the specified workbook with options for positioning.
    Uses the active workbook by default if no book_name is provided.

    Position Priority Order:
        1. at_start: Places sheet at the beginning
        2. at_end: Places sheet at the end
        3. before_sheet_name: Places sheet before specified sheet
        4. after_sheet_name: Places sheet after specified sheet

    Returns:
        str: Success message indicating sheet creation

    Examples:
        >>> excel_add_sheet("Sales2024")  # Add with specific name
        >>> excel_add_sheet(at_end=True)  # Add at end with default name
        >>> excel_add_sheet("Summary", book_name="Report.xlsx")  # Add to specific workbook
        >>> excel_add_sheet("Data", before_sheet_name="Sheet2")  # Add before existing sheet
    """
    before_sheet = None
    after_sheet = None

    if book_name is None:
        book = xw.books.active
    else:
        book = xw.books[book_name]

    if at_start:
        before_sheet = book.sheets[0]
    elif at_end:
        after_sheet = book.sheets[-1]
    elif before_sheet_name is not None:
        before_sheet = book.sheets[before_sheet_name]
    elif after_sheet_name is not None:
        after_sheet = book.sheets[after_sheet_name]

    book.sheets.add(name=name, before=before_sheet, after=after_sheet)

    return f"Successfully added a new sheet{' named ' + name if name else ''}."

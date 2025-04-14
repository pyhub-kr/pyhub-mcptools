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
    get_sheet,
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
def excel_find_data_ranges(
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
) -> str:
    """Detects and returns all distinct data block ranges in an Excel worksheet.

    Scans the used range of the worksheet to identify contiguous blocks of non-empty cells,
    interpreted as distinct tables. By default, it uses the active workbook and sheet unless
    `book_name` or `sheet_name` is specified.

    Detection Rules:
        - Identifies contiguous blocks of non-empty cells
        - Uses Excel’s native “table” expansion (`expand("table")`)
        - Empty or whitespace-only cells serve as block boundaries
        - Overlapping or adjacent blocks are merged to avoid duplication

    Returns:
        str: A JSON-encoded list of data range addresses (absolute reference format, e.g., ["A1:I11", "K1:P11"])

    Examples:
        >>> excel_find_data_ranges()
        >>> excel_find_data_ranges(book_name="Sales.xlsx")
        >>> excel_find_data_ranges(book_name="Report.xlsx", sheet_name="Q1")

    Best Practices:
        1. Use this function **before writing data** to avoid overwriting existing content.
        2. Leverage the returned ranges to:
            - Find suitable empty areas for new data
            - Suggest meaningful positions near related data blocks
            - Preserve worksheet structure and readability
        3. Integrate this step into your data workflow as a **pre-check** before any modification.

    Note:
        This function is particularly useful when automating Excel report generation,
        layout validation, or intelligent placement of new content within structured worksheets.
    """

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    data_ranges = []
    visited = set()

    used = sheet.used_range
    start_row = used.row
    start_col = used.column
    n_rows = used.rows.count
    n_cols = used.columns.count

    # 전체 데이터를 메모리로 한 번에 가져옴 (2D 리스트)
    data_grid = used.value

    # 엑셀 한 셀일 경우, data_grid 값은 단일 값이므로 보정
    if not isinstance(data_grid, list):
        data_grid = [[data_grid]]
    elif isinstance(data_grid[0], (str, int, float, type(None))):
        data_grid = [data_grid]

    for r in range(n_rows):
        for c in range(n_cols):
            abs_row = start_row + r
            abs_col = start_col + c
            addr = (abs_row, abs_col)

            if addr in visited:
                continue

            # 데이터 시작 부분에 대해서 범위 좌표 계산
            val = data_grid[r][c]
            if val is not None and str(val).strip() != "":
                cell = sheet.range((abs_row, abs_col))
                block = cell.expand("table")

                top = block.row
                left = block.column
                bottom = top + block.rows.count - 1
                right = left + block.columns.count - 1

                for rr in range(top, bottom + 1):
                    for cc in range(left, right + 1):
                        visited.add((rr, cc))

                # $ 기호를 제거한 범위 주소를 추가
                data_ranges.append(block.address.replace("$", ""))

    return json_dumps(data_ranges)


@mcp.tool()
@macos_excel_request_permission
def excel_get_values(
    sheet_range: Optional[ExcelRange] = Field(
        default=None,
        description="""Excel range to get data. If not specified, uses the entire used range of the sheet.
            Important: When using expand_mode, specify ONLY the starting cell (e.g., 'A1' not 'A1:B10')
            as the range will be automatically expanded.""",
        examples=["A1", "Sheet1!A1", "A1:C10"],  # expand_mode 사용 시에는 A1 형식만 사용
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
        description="""Mode for automatically expanding the selection range. When using expand_mode,
            specify ONLY the starting cell in sheet_range (e.g., 'A1').

            Supports:
            - "table": Expands only to the right and down from the starting cell
            - "right": Expands horizontally to include all contiguous data to the right
            - "down": Expands vertically to include all contiguous data below

            Note: All expand modes only work in the right/down direction from the starting cell.
                  No expansion occurs to the left or upward direction.""",
        examples=["table", "right", "down"],
    ),
) -> ExcelGetValuesResponse:
    """Get data from Excel workbook.

    Retrieves data from a specified Excel range. By default uses the active workbook and sheet
    if no specific book_name or sheet_name is provided.

    Important:
        When using expand_mode, specify ONLY the starting cell (e.g., 'A1') in sheet_range.
        The range will be automatically expanded based on the specified expand_mode.

    Returns:
        ExcelGetValuesResponse: A response model containing the data in CSV format.

    Examples:
        >>> excel_get_values("A1")  # Gets single cell value
        >>> excel_get_values("A1:B10")  # Gets fixed range in CSV format
        >>> excel_get_values("A1", expand_mode="table")  # Gets table data starting from A1
        >>> excel_get_values("B2", expand_mode="right")  # Gets row data starting from B2
        >>> excel_get_values("C1", expand_mode="down")  # Gets column data starting from C1
    """

    # expand_mode가 지정되어있을 때, 시트 범위에서 시작 셀 좌표만 추출.
    # Claude에서 expand_mode를 지정했을 때에도 sheet range를 너무 크게 잡을 때가 있음.
    if expand_mode is not None:
        sheet_range = sheet_range.split(":", 1)[0]

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
        examples=["A1:D10", "A:E"],
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

    if expand_mode is not None:
        sheet_range = sheet_range.split(":", 1)[0]

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

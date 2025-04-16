"""
Excel automation
"""

from pathlib import Path
from typing import Optional, Union

import xlwings as xw
from pydantic import Field
from xlwings.constants import HAlign, VAlign

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import (
    ExcelCellType,
    ExcelExpandMode,
    ExcelGetValuesResponse,
    ExcelHorizontalAlignment,
    ExcelVerticalAlignment,
)
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
from pyhub.mcptools.fs.utils import validate_path


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
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If None, uses active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
) -> str:
    """Detects and returns all distinct data block ranges in an Excel worksheet.

    Scans the used range of the worksheet to identify contiguous blocks of non-empty cells,
    interpreted as distinct tables. By default, it uses the active workbook and sheet unless
    `book_name` or `sheet_name` is specified.

    Detection Rules:
        - Identifies contiguous blocks of non-empty cells
        - Uses Excel's native "table" expansion (`expand("table")`)
        - Empty or whitespace-only cells serve as block boundaries
        - Overlapping or adjacent blocks are merged to avoid duplication

    Returns:
        str: A JSON-encoded list of data range addresses (absolute reference format, e.g., ["A1:I11", "K1:P11"])

    Examples:
        >>> excel_find_data_ranges()
        >>> excel_find_data_ranges(book_name="Sales.xlsx")
        >>> excel_find_data_ranges(book_name="Report.xlsx", sheet_name="Q1")

    Note:
        This function is particularly useful when automating Excel report generation,
        layout validation, or intelligent placement of new content within structured worksheets.
    """

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
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

                data_ranges.append(block.address)

    return json_dumps(data_ranges)


@mcp.tool(enabled=OS.current_is_windows())
@macos_excel_request_permission
def excel_get_special_cells_address(
    sheet_range: str = Field(
        default=None,
        description="""Excel range to get data. If not specified, uses the entire used range of the sheet.
            Important: When using expand_mode, specify ONLY the starting cell (e.g., 'A1' not 'A1:B10')
            as the range will be automatically expanded.""",
        examples=["A1", "Sheet1!A1", "A1:C10"],
    ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If not specified, uses the active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If not specified, uses the active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
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
    cell_type_filter: Optional[ExcelCellType] = Field(
        None,
        description=f"""Special Cells Filter : {dict(((v.value, v.label) for v in ExcelCellType))}""",
    ),
) -> str:
    """Get the address of special cells in an Excel worksheet based on specified criteria.

    Args:
        sheet_range (str, optional): Target Excel range. Uses entire used range if not specified.
        book_name (str, optional): Target workbook name. Uses active workbook if not specified.
        sheet_name (str, optional): Target sheet name. Uses active sheet if not specified.
        expand_mode (ExcelExpandMode, optional): Mode for expanding selection ('table', 'right', 'down').
        cell_type_filter (ExcelCellType, optional): Filter for special cell types.

    Returns:
        str: Address of the special cells range.

    Note:
        Windows-only feature.
    """

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
    range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )

    if cell_type_filter:
        return range_.api.SpecialCells(cell_type_filter.value).Address

    return range_.get_address()


@mcp.tool()
@macos_excel_request_permission
def excel_get_values(
    sheet_range: str = Field(
        description="""Excel range to get data. If not specified, uses the entire used range of the sheet.
            Important: When using expand_mode, specify ONLY the starting cell (e.g., 'A1' not 'A1:B10')
            as the range will be automatically expanded.""",
        examples=["A1", "Sheet1!A1", "A1:C10"],  # expand_mode 사용 시에는 A1 형식만 사용
    ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If not specified, uses the active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If not specified, uses the active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
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

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
    range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )
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
    sheet_range: str = Field(
        description="Excel range where to write the data",
        examples=["A1", "B2:B10", "Sheet1!A1:C5"],
    ),
    values: str = Field(description="CSV string"),
    # csv_abs_path: Optional[str] = Field(
    #     default=None,
    #     description="""Absolute path to the CSV file to read.
    #         If specified, this will override any value provided in the 'values' parameter.
    #         Either 'csv_abs_path' or 'values' must be provided, but not both.""",
    #     examples=["/path/to/data.csv"],
    # ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If None, uses active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
) -> str:
    """Write data to a specified range in an Excel workbook.

    When adding values to consecutive cells, you only need to specify the starting cell coordinate,
    and the data will be populated according to the dimensions of the input.

    Range Format Rules:
        - For multiple columns (e.g., "A1:C1"), ensure data matches the range width
        - For multiple rows (e.g., "A1:A10"), ensure data matches the range height
        - Each row must have the same number of columns
        - Each column must have the same number of rows

    Returns:
        str: The address of the range where data was written (e.g., "A1:C3").
             This represents the actual range that was populated with data.

    Examples:
        # CSV format
        >>> excel_set_values("A1", "v1,v2,v3\\nv4,v5,v6")  # 2x3 grid using CSV
    """
    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

    # if csv_abs_path is not None:
    #     csv_path: Path = validate_path(csv_abs_path)
    #     with csv_path.open("rt", encoding="utf-8") as f:
    #         values = csv_loads(f.read())

    # if values is not None:
    if values.strip().startswith(("[", "{")):
        data = json_loads(values)
    else:
        data = csv_loads(values)
    # else:
    #     raise ValueError("Either csv_abs_path or values must be provided.")

    range_.value = fix_data(sheet_range, data)

    return range_.expand("table").get_address()


@mcp.tool()
@macos_excel_request_permission
def excel_set_styles(
    sheet_range: str = Field(
        description=(
            "Excel range to apply styles. Supports both continuous ranges (e.g., 'A1:C5') "
            "and discontinuous ranges (e.g., 'A1,C3,D5')."
        ),
        examples=["A1", "B2:B10", "Sheet1!A1:C5", "A1,C3,D5", "A1:B2,D4:E6"],
    ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If None, uses active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
    expand_mode: Optional[ExcelExpandMode] = Field(
        default=None,
        description="""Mode for automatically expanding the selection range. Options:
            - "table": Expands right and down from starting cell
            - "right": Expands horizontally to include contiguous data
            - "down": Expands vertically to include contiguous data""",
        examples=["table", "right", "down"],
    ),
    reset: bool = Field(
        default=False,
        description="If True, resets all styles to default values before applying new styles.",
    ),
    background_color: Optional[str] = Field(
        default=None,
        description="RGB color for cell background (e.g., '255,255,0' for yellow)",
        examples=["255,255,0", "255,0,0"],
    ),
    font_color: Optional[str] = Field(
        default=None,
        description="RGB color for font (e.g., '255,0,0' for red)",
        examples=["255,0,0", "0,0,255"],
    ),
    bold: Optional[bool] = Field(
        default=False,
        description="If True, makes the font bold.",
    ),
    italic: Optional[bool] = Field(
        default=False,
        description="If True, makes the font italic.",
    ),
    strikethrough: Optional[bool] = Field(
        default=False,
        description="If True, adds strikethrough to text. Windows only.",
    ),
    underline: Optional[bool] = Field(
        default=False,
        description="If True, adds underline to text. Windows only.",
    ),
    horizontal_alignment: Optional[ExcelHorizontalAlignment] = Field(
        None,
        description=f"""The horizontal alignment of the cells. Windows only.
{dict(((v.value, v.label) for v in ExcelHorizontalAlignment))}""",
    ),
    vertical_alignment: Optional[ExcelVerticalAlignment] = Field(
        None,
        description=f"""The vertical alignment of the cells. Windows only.
{dict(((v.value, v.label) for v in ExcelVerticalAlignment))}""",
    ),
) -> str:
    """Apply styles to a specified range in an Excel workbook.

    Applies various formatting options to cells in the specified range. Uses the active workbook
    and sheet by default if no specific book_name or sheet_name is provided.

    Style Options:
        - Colors: Background and font colors using RGB format (e.g., '255,255,0' for yellow)
        - Font styles: Bold and italic
        - Windows-only features:
            - Text decoration: Strikethrough and underline
            - Alignment: Horizontal and vertical cell alignment
        - Reset: Resets all styles to default values before applying new styles

    Range Format Support:
        - Single cell: 'A1'
        - Continuous range: 'A1:C5'
        - Sheet-specific range: 'Sheet1!A1:C5'
        - Discontinuous ranges: 'A1,C3,D5' or 'A1:B2,D4:E6'

    Returns:
        str: The address of the range where styles were applied.

    Examples:
        >>> excel_set_styles("A1:B10", background_color="255,255,0")  # Yellow background
        >>> excel_set_styles("C1", bold=True, italic=True)  # Bold and italic text
        >>> excel_set_styles("Sheet1!D1:D10", font_color="255,0,0")  # Red text
        >>> excel_set_styles("A1:C5", horizontal_alignment="center")  # Center align (Windows only)
        >>> excel_set_styles("A1:B10", reset=True)  # Reset all styles to default
    """

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
    range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )

    def make_tuple(rgb_code: str) -> tuple[int, int, int]:
        r, g, b = tuple(map(int, rgb_code.split(",")))
        return r, g, b

    if reset:
        range_.color = None
        range_.font.color = None
        range_.font.bold = False
        range_.font.italic = False

        range_.number_format = "General"

        if OS.current_is_windows():
            # range_.font.name = None  # 값만 변경될 뿐, 리셋 X
            # range_.font.size = None  # 값만 변경될 뿐, 리셋 X
            range_.api.WrapText = False
            # range_.api.Borders.LineStyle = -4142  # What ?
            range_.api.IndentLevel = 0
            range_.api.ShrinkToFit = False
            # range_.api.MergeCells = False  # 병합된 셀에 걸쳐져있어도 셀 병합 해제

            range_.api.Strikethrough = False  # Reset strikethrough
            range_.api.Underline = False  # Reset underline
            range_.api.HorizontalAlignment = HAlign.left  # Reset horizontal alignment
            range_.api.VerticalAlignment = VAlign.bottom  # Reset vertical alignment
            range_.api.Orientation = 0  # Reset text rotation
            # range_.api.ReadingOrder = xlLTR  # Not found xlLTR

            # Reset conditional formatting
            range_.api.FormatConditions.Delete()

            # Reset validation
            range_.api.Validation.Delete()

    # Apply new styles if specified
    if background_color is not None:
        range_.color = make_tuple(background_color)

    if font_color is not None:
        range_.font.color = make_tuple(font_color)

    if bold is not None:
        range_.font.bold = bold

    if italic is not None:
        range_.font.italic = italic

    if OS.current_is_windows():
        if strikethrough is not None:
            range_.api.Strikethrough = strikethrough

        if underline is not None:
            range_.api.Underline = underline

        if horizontal_alignment is not None:
            range_.api.HorizontalAlignment = horizontal_alignment

        if vertical_alignment is not None:
            range_.api.VerticalAlignment = vertical_alignment

    return range_.expand("table").get_address()


@mcp.tool()
@macos_excel_request_permission
def excel_autofit(
    sheet_range: str = Field(
        description="Excel range to autofit",
        examples=["A1:D10", "A:E"],
    ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If None, uses active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
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

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
    range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )
    range_.autofit()


@mcp.tool()
@macos_excel_request_permission
def excel_set_formula(
    sheet_range: str = Field(
        description="Excel range where to apply the formula",
        examples=["A1", "B2:B10", "Sheet1!C1:C10"],
    ),
    formula: str = Field(
        description="Excel formula to set. Must start with '=' and follow Excel formula syntax.",
        examples=["=SUM(B1:B10)", "=A1*B1", "=VLOOKUP(A1, Sheet2!A:B, 2, FALSE)"],
    ),
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to use. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
    # sheet_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of sheet to use. If None, uses active sheet.",
    #     examples=["Sheet1", "Sales2023"],
    # ),
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

    book_name, sheet_name = None, None  # TODO: Cursor 타입 이슈로 인자를 임시 제거
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
    # book_name: Optional[str] = Field(
    #     default=None,
    #     description="Name of workbook to add sheet to. If None, uses active workbook.",
    #     examples=["Sales.xlsx", "Report2023.xlsx"],
    # ),
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

    book_name = None  # TODO: Cursor 타입 이슈로 인자를 임시 제거

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

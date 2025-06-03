import asyncio
from typing import Literal

import xlwings as xw
from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.microsoft.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.microsoft.excel.utils import (
    get_sheet,
    json_dumps,
    normalize_text,
)
from pyhub.mcptools.microsoft.excel.utils.tables import PivotTable

# Default timeout for Excel operations
EXCEL_DEFAULT_TIMEOUT = 60

# Converted from delegator pattern to direct implementation
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_get_opened_workbooks() -> str:
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

    @macos_excel_request_permission
    def _get_opened_workbooks():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
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
                                    "range": sheet.used_range.get_address(),
                                    "count": sheet.used_range.count,
                                    "shape": sheet.used_range.shape,
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
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_get_opened_workbooks)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_get_values(
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
        default="",
        description="Mode for automatically expanding the selection range (table/down/right/none)",
    ),
    value_type: str = Field(
        default="values",
        description="Type of data to retrieve (values/formula2)",
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

    @macos_excel_request_permission
    def _get_values():
        from pyhub.mcptools.microsoft.excel.utils import (
            get_range,
            convert_to_csv,
            cleanup_excel_com,
        )

        try:
            range_ = get_range(
                sheet_range=sheet_range,
                book_name=book_name,
                sheet_name=sheet_name,
                expand_mode=expand_mode,
            )

            values = range_.value

            # Process according to value_type
            if value_type == "formula2":
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
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_get_values)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_set_values(
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

    @macos_excel_request_permission
    def _set_values():
        from pathlib import Path
        from pyhub.mcptools.microsoft.excel.utils import (
            get_range,
            fix_data,
            csv_loads,
            json_loads,
            cleanup_excel_com,
        )
        from pyhub.mcptools.fs.utils import validate_path

        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

            if csv_abs_path:
                csv_path: Path = validate_path(csv_abs_path)
                with csv_path.open("rt", encoding="utf-8") as f:
                    values_to_use = f.read()
            else:
                values_to_use = values

            if values_to_use is not None:
                if values_to_use.strip().startswith(("[", "{")):
                    data = json_loads(values_to_use)
                else:
                    data = csv_loads(values_to_use)
            else:
                raise ValueError("Either csv_abs_path or values must be provided.")

            range_.value = fix_data(sheet_range, data)

            return f"Successfully set values to {range_.address}."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_set_values)


# New integrated info tool
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_get_info(
    info_type: Literal["workbooks", "charts", "pivot_tables", "special_cells"] = Field(
        description="Type of information to retrieve"
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
    # special_cells specific parameters
    sheet_range: str = Field(
        default="",
        description="Excel cell range for special_cells operation. Optional.",
        examples=["A1", "A1:D10", "B:E", "3:7"],
    ),
    expand_mode: str = Field(
        default="none",
        description="Range expansion mode for special_cells (table, down, right, none)",
    ),
    cell_type_filter: int = Field(
        default=0,
        description="Cell type filter for special_cells (xlCellTypeConstants=2, xlCellTypeFormulas=4, etc.)",
    ),
) -> str:
    """Get various information from Excel workbooks and sheets.

    Operations:
    - workbooks: List all open workbooks and their sheets
    - charts: Get charts in a specific sheet
    - pivot_tables: Get pivot tables in a specific sheet
    - special_cells: Get special cells address (Windows only)

    Returns:
        JSON string with requested information
    """

    @macos_excel_request_permission
    def _get_workbooks():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
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
                                    "range": sheet.used_range.get_address(),
                                    "count": sheet.used_range.count,
                                    "shape": sheet.used_range.shape,
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
        finally:
            cleanup_excel_com()

    @macos_excel_request_permission
    def _get_charts():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
            return json_dumps(
                [
                    {
                        "name": chart.name,
                        "left": chart.left,
                        "top": chart.top,
                        "width": chart.width,
                        "height": chart.height,
                        "index": i,
                    }
                    for i, chart in enumerate(sheet.charts)
                ]
            )
        finally:
            cleanup_excel_com()

    @macos_excel_request_permission
    def _get_pivot_tables():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
            return json_dumps(PivotTable.list(sheet))
        finally:
            cleanup_excel_com()

    @macos_excel_request_permission
    def _get_special_cells():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            if not OS.current_is_windows():
                return json_dumps({"error": "special_cells is only available on Windows"})

            from pyhub.mcptools.microsoft.excel.types import ExcelCellType
            from pyhub.mcptools.microsoft.excel.utils import get_range

            range_ = get_range(
                sheet_range=sheet_range or "A1",
                book_name=book_name,
                sheet_name=sheet_name,
                expand_mode=expand_mode,
            )

            cell_type = cell_type_filter or ExcelCellType.get_none_value()
            special_cells_range = range_.api.SpecialCells(cell_type)

            return json_dumps({"address": special_cells_range.Address})
        finally:
            cleanup_excel_com()

    # Execute the appropriate function based on info_type
    if info_type == "workbooks":
        return await asyncio.to_thread(_get_workbooks)
    elif info_type == "charts":
        return await asyncio.to_thread(_get_charts)
    elif info_type == "pivot_tables":
        return await asyncio.to_thread(_get_pivot_tables)
    elif info_type == "special_cells":
        return await asyncio.to_thread(_get_special_cells)
    else:
        return json_dumps({"error": f"Unknown info_type: {info_type}"})


# New integrated set_cell_data tool
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_set_cell_data(
    data_type: Literal["values", "formula"] = Field(description="Type of data to set"),
    sheet_range: str = Field(
        description="Excel cell range to set data to",
        examples=["A1", "A1:D10", "B:E", "3:7", "Sheet1!A1:D10"],
    ),
    data: str = Field(
        description="Data to set. For values: CSV or JSON string. For formula: Excel formula starting with '='",
        examples=["v1,v2,v3\\nv4,v5,v6", "[[1,2,3],[4,5,6]]", "=SUM(B1:B10)"],
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
    # values specific parameter
    csv_abs_path: str = Field(
        default="",
        description="Absolute path to CSV file (values only). Overrides 'data' parameter if provided.",
        examples=["/path/to/data.csv"],
    ),
) -> str:
    """Set values or formulas in Excel cells.

    Operations:
    - values: Set cell values from CSV/JSON string or CSV file
    - formula: Set Excel formula to specified range

    Performance Tips:
    - For multiple cells, use range notation (e.g., "A1:B10") instead of individual calls
    - CSV format with ranges is faster than separate calls per cell

    Returns:
        Success message
    """

    @macos_excel_request_permission
    def _set_values():
        from pathlib import Path

        from pyhub.mcptools.fs.utils import validate_path
        from pyhub.mcptools.microsoft.excel.utils import (
            csv_loads,
            fix_data,
            get_range,
            json_loads,
            cleanup_excel_com,
        )

        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)

            values_to_set = data
            if csv_abs_path:
                csv_path: Path = validate_path(csv_abs_path)
                with csv_path.open("rt", encoding="utf-8") as f:
                    values_to_set = f.read()

            if values_to_set is not None:
                if values_to_set.strip().startswith(("[", "{")):
                    parsed_data = json_loads(values_to_set)
                else:
                    parsed_data = csv_loads(values_to_set)
            else:
                parsed_data = None

            if parsed_data is not None:
                fixed_data = fix_data(parsed_data)
                range_.value = fixed_data

            return "Successfully set values."
        finally:
            cleanup_excel_com()

    @macos_excel_request_permission
    def _set_formula():
        from pyhub.mcptools.microsoft.excel.utils import get_range, cleanup_excel_com

        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
            range_.formula2 = data

            return "Successfully set formula."
        finally:
            cleanup_excel_com()

    # Execute the appropriate function based on data_type
    if data_type == "values":
        if csv_abs_path and data:
            return json_dumps({"error": "Provide either 'data' or 'csv_abs_path', not both"})
        return await asyncio.to_thread(_set_values)
    elif data_type == "formula":
        if csv_abs_path:
            return json_dumps({"error": "csv_abs_path is not valid for formula operation"})
        if not data.startswith("="):
            return json_dumps({"error": "Formula must start with '='"})
        return await asyncio.to_thread(_set_formula)
    else:
        return json_dumps({"error": f"Unknown data_type: {data_type}"})


# Independent tools with direct implementation
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_find_data_ranges(
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
    """Detects and returns all distinct data block ranges in an Excel worksheet.

    Scans worksheet to find contiguous blocks of non-empty cells.
    Uses active workbook/sheet if not specified.

    Detection Rules:
        - Finds contiguous non-empty cell blocks
        - Uses Excel's table expansion
        - Empty cells act as block boundaries
        - Merges overlapping/adjacent blocks

    Returns:
        str: JSON list of range addresses (e.g., ["A1:I11", "K1:P11"])
    """

    @macos_excel_request_permission
    def _find_data_ranges():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

            data_ranges = []
            visited = set()

            # Get all values in used range
            used_range = sheet.used_range
            if not used_range:
                return json_dumps([])

            values = used_range.value
            if not values:
                return json_dumps([])

            # Convert to 2D array if single cell
            if not isinstance(values, list):
                values = [[values]]
            elif values and not isinstance(values[0], list):
                values = [values]

            # Scan for data blocks
            for row_idx, row in enumerate(values):
                for col_idx, cell_value in enumerate(row):
                    if cell_value is not None and (row_idx, col_idx) not in visited:
                        # Found non-empty cell, expand to find full data block
                        cell = used_range.cells[row_idx, col_idx]
                        data_block = cell.expand("table")

                        # Mark all cells in this block as visited
                        block_start_row = data_block.row - used_range.row
                        block_start_col = data_block.column - used_range.column
                        block_rows = data_block.rows.count
                        block_cols = data_block.columns.count

                        for r in range(block_start_row, block_start_row + block_rows):
                            for c in range(block_start_col, block_start_col + block_cols):
                                visited.add((r, c))

                        data_ranges.append(data_block.get_address())

            return json_dumps(data_ranges)
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_find_data_ranges)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_set_styles(
    styles: str = Field(
        description="Style specifications in CSV format or single style string",
        examples=[
            "A1:B2;background_color=255,255,0;font_color=0,0,255;bold=true;italic=false",
            'book_name,sheet_name,range,background_color,...\nSales.xlsx,Sheet1,A1:B2,"255,255,0",...',
        ],
    ),
) -> str:
    """Apply formatting styles to Excel cells.

    Supports two input formats:
    1. Single style: "range;option1=value1;option2=value2"
    2. Multiple styles CSV: "book_name,sheet_name,range,background_color,font_color,bold,italic,expand_mode"

    Style Options:
        - background_color: RGB values (e.g., "255,255,0" for yellow)
        - font_color: RGB values (e.g., "0,0,255" for blue)
        - bold: true/false
        - italic: true/false
        - expand_mode: table/down/right/none

    Returns:
        str: Success message with applied ranges
    """

    @macos_excel_request_permission
    def _set_styles():
        from pyhub.mcptools.microsoft.excel.utils import (
            csv_loads,
            get_range,
            cleanup_excel_com,
        )

        def apply_styles(excel_range, style_data):
            """Apply style options to a range."""
            # Background color
            bg_color = style_data.get("background_color")
            if bg_color:
                if isinstance(bg_color, str):
                    rgb = tuple(int(x.strip()) for x in bg_color.split(","))
                else:
                    rgb = bg_color
                excel_range.color = rgb

            # Font color
            font_color = style_data.get("font_color")
            if font_color:
                if isinstance(font_color, str):
                    rgb = tuple(int(x.strip()) for x in font_color.split(","))
                else:
                    rgb = font_color
                excel_range.font.color = rgb

            # Bold
            bold = style_data.get("bold")
            if bold is not None:
                excel_range.font.bold = str(bold).lower() == "true"

            # Italic
            italic = style_data.get("italic")
            if italic is not None:
                excel_range.font.italic = str(italic).lower() == "true"

        def parse_single_style(style_str):
            """Parse single style format."""
            parts = style_str.split(";")
            range_spec = parts[0]

            # Check if range includes book/sheet
            book_name = ""
            sheet_name = ""
            if "!" in range_spec:
                sheet_part, range_part = range_spec.split("!", 1)
                if ".xlsx" in sheet_part:
                    book_name = sheet_part
                else:
                    sheet_name = sheet_part
                range_spec = range_part

            options = {}
            for part in parts[1:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    options[key.strip()] = value.strip()

            return book_name, sheet_name, range_spec, options

        try:
            selected_ranges = []

            # Detect format and process
            if "\n" in styles or styles.startswith("book_name,"):
                # CSV format - convert to list of dicts
                rows = csv_loads(styles)
                if rows and isinstance(rows[0], list):
                    # Convert list of lists to list of dicts
                    headers = rows[0]
                    dict_rows = []
                    for row in rows[1:]:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                row_dict[header] = row[i]
                        dict_rows.append(row_dict)
                    rows = dict_rows

                for row_data in rows:
                    excel_range = get_range(
                        sheet_range=row_data.get("range", ""),
                        book_name=row_data.get("book_name", ""),
                        sheet_name=row_data.get("sheet_name", ""),
                        expand_mode=row_data.get("expand_mode", ""),
                    )
                    apply_styles(excel_range, row_data)
                    selected_ranges.append(excel_range)
            else:
                # Single style format
                book_name, sheet_name, range_spec, options = parse_single_style(styles)
                excel_range = get_range(
                    sheet_range=range_spec,
                    book_name=book_name,
                    sheet_name=sheet_name,
                    expand_mode=options.get("expand_mode", ""),
                )
                apply_styles(excel_range, options)
                selected_ranges.append(excel_range)

            addresses = ",".join(r.get_address() for r in selected_ranges)
            return f"Successfully set styles to {addresses}."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_set_styles)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_autofit(
    sheet_range: str = Field(
        description="Excel range to autofit",
        examples=["A1:D10", "A:E"],
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
        default="none",
        description="Mode for automatically expanding the selection range (table/down/right/none)",
    ),
) -> str:
    """Automatically adjusts column widths to fit the content in the specified Excel range.

    Returns:
        str: Success message
    """

    @macos_excel_request_permission
    def _autofit():
        from pyhub.mcptools.microsoft.excel.utils import get_range, cleanup_excel_com

        try:
            range_ = get_range(
                sheet_range=sheet_range,
                book_name=book_name,
                sheet_name=sheet_name,
                expand_mode=expand_mode,
            )
            range_.autofit()

            return "Successfully autofit."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_autofit)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_add_sheet(
    name: str = Field(
        default="",
        description="Name for the new sheet. Auto-generated if not provided.",
        examples=["NewSheet", "Data2024"],
    ),
    book_name: str = Field(
        default="",
        description="Name of workbook to use. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    at_start: bool = Field(
        default=False,
        description="Add sheet at the beginning",
    ),
    at_end: bool = Field(
        default=False,
        description="Add sheet at the end",
    ),
    before_sheet_name: str = Field(
        default="",
        description="Add new sheet before this sheet",
        examples=["Sheet2"],
    ),
    after_sheet_name: str = Field(
        default="",
        description="Add new sheet after this sheet",
        examples=["Sheet1"],
    ),
) -> str:
    """Add a new sheet to an Excel workbook.

    Position options (in priority order):
    1. at_start: First position
    2. at_end: Last position
    3. before_sheet_name: Before specified sheet
    4. after_sheet_name: After specified sheet
    5. Default: After active sheet

    Returns:
        str: Success message with sheet name
    """

    @macos_excel_request_permission
    def _add_sheet():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            # Get the workbook
            if book_name:
                book = xw.books[book_name]
            else:
                book = xw.books.active

            # Determine position
            if at_start:
                before = 0
                after = None
            elif at_end:
                before = None
                after = -1
            elif before_sheet_name:
                before = book.sheets[before_sheet_name]
                after = None
            elif after_sheet_name:
                before = None
                after = book.sheets[after_sheet_name]
            else:
                # Default: after current sheet
                before = None
                after = None

            # Add sheet
            sheet = book.sheets.add(
                name=name or None,
                before=before,
                after=after,
            )

            if name:
                return f"Successfully added sheet '{sheet.name}'."
            else:
                return "Successfully added sheet."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_add_sheet)

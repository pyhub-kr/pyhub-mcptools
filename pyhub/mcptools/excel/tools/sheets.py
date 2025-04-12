"""
Excel automation
"""

from typing import Optional, Union

import xlwings as xw

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import ExcelExpandMode, ExcelFormula, ExcelRange
from pyhub.mcptools.excel.utils import convert_to_csv, fix_data, get_range, json_dumps, json_loads, normalize_text


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
    sheet_range: Optional[ExcelRange] = None,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    expand_mode: Optional[ExcelExpandMode] = None,
) -> str:
    """Get data from Excel workbook.

    Retrieves data from a specified Excel range. By default uses the active workbook and sheet
    if no specific book_name or sheet_name is provided.

    Parameters:
        sheet_range: Excel range to get data from (e.g., "A1:C10"). If None, gets entire used range.
        book_name: Name of workbook to use. If None, uses active workbook.
        sheet_name: Name of sheet to use. If None, uses active sheet.
        expand_mode: Mode for automatically expanding the selection range. Supports:
            - "table": Expands only to the right and down from the starting cell
            - "right": Expands horizontally to include all contiguous data to the right
            - "down": Expands vertically to include all contiguous data below
            Note: All expand modes only work in the right/down direction from the starting cell.
                  No expansion occurs to the left or upward direction.

    Returns:
        String containing the data in CSV format.

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
        return ""

    # Convert single value to 2D list format
    if not isinstance(data, list):
        data = [[data]]
    elif data and not isinstance(data[0], list):
        data = [data]

    return convert_to_csv(data)


@mcp.tool()
@macos_excel_request_permission
def excel_set_values(
    sheet_range: ExcelRange,
    json_values: Union[str, list],
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    autofit: bool = False,
) -> None:
    """Write data to a specified range in the active sheet of an open Excel workbook.

    When adding values to consecutive cells, you only need to specify the starting cell coordinate,
    and the data will be populated according to the dimensions of the input.

    IMPORTANT: The data orientation (row vs column) is determined by the format of json_values:
    - Flat list ["v1", "v2", "v3"] will always be written horizontally (row orientation)
    - Nested list [["v1"], ["v2"], ["v3"]] will be written vertically (column orientation)

    If your sheet_range spans multiple columns (e.g., "A1:C1"), use a flat list format.
    If your sheet_range spans multiple rows (e.g., "A1:A10"), you MUST use a nested list format.

    The dimensions of the input must match the expected format:
    - For rows, each row must have the same number of columns
    - For columns, each column must have the same number of rows

    Parameters:
        sheet_range (ExcelRange): Excel range where to write the data (e.g., "A1", "B2:B10").
        json_values (Union[str, list]): Data to write, either as a JSON string or Python list.
        book_name (Optional[str], optional): Name of workbook to use. Defaults to None (active workbook).
        sheet_name (Optional[str], optional): Name of sheet to use. Defaults to None (active sheet).
        autofit (bool, optional): If True, automatically adjusts the column widths to fit the content.
                                Defaults to False.

    Examples:
    - Write horizontally (1 row): sheet_range="A10" json_values='["v1", "v2", "v3"]'
    - Write vertically (1 column): sheet_range="A10" json_values='[["v1"], ["v2"], ["v3"]]'
    - Multiple rows/columns: sheet_range="A10" json_values='[["v1", "v2"], ["v3", "v4"]]'

    INCORRECT USAGE:
    - DO NOT use sheet_range="A1:A5" with json_values='["v1", "v2", "v3", "v4", "v5"]'
      This will write horizontally instead of vertically.
    - CORRECT way: sheet_range="A1:A5" json_values='[["v1"], ["v2"], ["v3"], ["v4"], ["v5"]]'
    """

    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    range_.value = fix_data(sheet_range, json_loads(json_values))

    if autofit:
        range_.autofit()


@mcp.tool()
@macos_excel_request_permission
def excel_autofit(
    sheet_range: ExcelRange,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    expand_mode: Optional[ExcelExpandMode] = None,
) -> None:
    """Automatically adjusts column widths to fit the content in the specified Excel range.

    Adjusts the width of columns in the specified range to fit the content, making all data visible
    without truncation. By default uses the active workbook and sheet if no specific book_name
    or sheet_name is provided.

    Parameters:
        sheet_range (ExcelRange): Excel range to autofit (e.g., "A1:C10", "B:B" for entire column).
        book_name (Optional[str], optional): Name of workbook to use. Defaults to None (active workbook).
        sheet_name (Optional[str], optional): Name of sheet to use. Defaults to None (active sheet).
        expand_mode (Optional[ExcelExpandMode], optional): Mode for automatically expanding the selection range.
            Supports:
            - "table": Expands only to the right and down from the starting cell
            - "right": Expands horizontally to include all contiguous data to the right
            - "down": Expands vertically to include all contiguous data below
            Note: All expand modes only work in the right/down direction from the starting cell.
                  No expansion occurs to the left or upward direction.

    Examples:
        >>> excel_autofit("A1:D10")  # Autofit specific range
        >>> excel_autofit("A:E")     # Autofit entire columns A through E
        >>> excel_autofit("A:A", book_name="Sales.xlsx", sheet_name="Q1")  # Autofit column A in specific sheet
        >>> excel_autofit("A1", expand_mode="table")  # Autofit all contiguous data to the right and down from A1
        >>> excel_autofit("A1", expand_mode="right")  # Autofit all contiguous data to the right of A1
        >>> excel_autofit("A1", expand_mode="down")   # Autofit all contiguous data below A1
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    if expand_mode is not None:
        range_ = range_.expand(mode=expand_mode.value.lower())
    range_.autofit()


@mcp.tool()
@macos_excel_request_permission
def excel_set_formula(
    sheet_range: ExcelRange,
    formula: ExcelFormula,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
):
    """Set a formula in a specified range of an Excel workbook.

    Applies an Excel formula to the specified range. The formula will be evaluated by Excel
    after being set. Uses the active workbook and sheet if no specific book_name or sheet_name
    is provided.

    Parameters:
        sheet_range (ExcelRange): Excel range where the formula should be applied (e.g., "A1", "B2:B10").
            For multiple cells, the formula will be adjusted relatively.
        formula (ExcelFormula): Excel formula to set. Must start with "=" and follow Excel formula syntax.
        book_name (Optional[str], optional): Name of workbook to use. Defaults to None, which uses active workbook.
        sheet_name (Optional[str], optional): Name of sheet to use. Defaults to None, which uses active sheet.

    Note:
        - The formula will be applied using Excel's formula2 property, which supports modern
          Excel features and dynamic arrays.
        - When applying to a range of cells, Excel will automatically adjust cell references
          in the formula according to each cell's position.
        - Formulas must follow Excel's syntax rules and use valid function names and cell references.
        - Array formulas (CSE formulas) are supported and will be automatically detected by Excel.

    Examples:
        >>> excel_set_formula("A1", "=SUM(B1:B10)")
        >>> excel_set_formula("C1:C10", "=A1*B1", book_name="Sales.xlsx", sheet_name="Q1")
        >>> excel_set_formula("D1", "=VLOOKUP(A1, Sheet2!A:B, 2, FALSE)")
    """
    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    range_.formula2 = formula


@mcp.tool()
@macos_excel_request_permission
def excel_add_sheet(
    name: Optional[str] = None,
    book_name: Optional[str] = None,
    at_start: bool = False,
    at_end: bool = False,
    before_sheet_name: Optional[str] = None,
    after_sheet_name: Optional[str] = None,
) -> str:
    """
    Adds a new sheet to the specified Excel workbook.

    Parameters:
        name (Optional[str]): The name of the new sheet. If None, Excel assigns a default name (e.g., "Sheet1").
        book_name (Optional[str]): The name of the workbook to add the sheet to.
                                   If None, the currently active workbook is used.
        at_start (bool): If True, adds the sheet at the beginning of the workbook. Default is False.
        at_end (bool): If True, adds the sheet at the end of the workbook. Default is False.
        before_sheet_name (Optional[str]): The name of the sheet before which the new sheet should be inserted.
                                           Optional.
        after_sheet_name (Optional[str]): The name of the sheet after which the new sheet should be inserted.
                                          Optional.

    Returns:
        str: A message indicating the sheet has been successfully added.

    Note:
        - Parameters for sheet placement have the following priority order:
            at_start > at_end > before_sheet_name > after_sheet_name.
        - If multiple placement parameters are provided, only the highest priority one will be considered.
        - The function uses xlwings and requires an active Excel session.
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

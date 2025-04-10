"""
Excel automation
"""

import json
import re
from ast import literal_eval
from typing import Optional, Union

import xlwings as xw

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.types import ExcelFormula, ExcelRange

#
# macOS 보안정책에 창의 가시성을 조절하거나, 워크북 수를 세는 명령은 자동화 권한을 허용한 앱에서만 가능
# Claude 앱에서는 Excel에 대해 자동화 권한을 부여하지 않았음.
#
# Claude 앱내에서 STDIN 방식의 직접 실행 방식이기에 CLAUDE 앱의 실행권한이 영향을 받음.
# MCP Server를 별도 서버로 띄우고, SSE 방식으로 접근한다면 이를 해결할 수도 있겠음.
# 장기적으로 별도 애플리케이션으로 띄울 수 있어야, 다양한 기능 구현이 가능하겠음.
#
#  - https://github.com/xlwings/xlwings/issues/1262
#  - https://github.com/xlwings/xlwings/issues/1851
#  - https://github.com/xlwings/xlwings/issues/1966
#
# Claude 밖에서 별도 프로세스로 SSE 서버를 띄운 다음 pyhub.mcptools.excel run sse --port 9999
# Claude 에서는 uvx mcp-proxy http://localhost:9999/sse 명령으로 접속 가능
#


@mcp.tool()
def excel_get_opened_workbooks() -> str:
    """Get a list of all open workbooks and their sheets in Excel"""

    return json_dumps(
        {
            "books": [
                {
                    "name": book.name,
                    "fullname": book.fullname,
                    "sheets": [
                        {
                            "name": sheet.name,
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
def excel_get_values(
    sheet_range: Optional[ExcelRange] = None,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> str:
    """Get data from Excel workbook.

    Retrieves data from a specified Excel range. By default uses the active workbook and sheet
    if no specific book_name or sheet_name is provided.

    Parameters:
        sheet_range: Excel range to get data from (e.g., "A1:C10"). If None, gets entire used range.
        book_name: Name of workbook to use. If None, uses active workbook.
        sheet_name: Name of sheet to use. If None, uses active sheet.

    Returns:
        JSON string containing the data.
    """

    range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
    data = range_.value

    if data is None:
        return "[]"

    return json_dumps(data)


@mcp.tool()
def excel_set_values(
    sheet_range: ExcelRange,
    json_values: Union[str, list],
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
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


@mcp.tool()
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
            Examples:
            - "=SUM(A1:A10)"
            - "=AVERAGE(B1:B5)"
            - "=CONCATENATE(A1, \" \", B1)"
            - "=IF(A1>10, \"High\", \"Low\")"
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


def get_range(
    sheet_range: ExcelRange,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> xw.Range:
    if book_name is None:
        book = xw.books.active
    else:
        book = xw.books[book_name]

    if sheet_name is None:
        sheet = book.sheets.active
    else:
        sheet = book.sheets[sheet_name]

    if sheet_range is None:
        range_ = sheet.used_range
    else:
        range_ = sheet.range(sheet_range)

    return range_


def fix_data(sheet_range: ExcelRange, values: Union[str, list]) -> Union[str, list]:
    """
    sheet_range가 열 방향인데, 값이 리스트이지만 중첩 리스트가 아니라면 중첩 리스트로 변환합니다.

    Args:
        sheet_range: Excel 범위 문자열 (예: "A1:A10", "B1", "Sheet1!C1:C5")
        values: 셀에 입력할 값들

    Returns:
        변환된 값 또는 원본 값
    """

    if (
        isinstance(values, str)
        or not isinstance(values, list)
        or (isinstance(values, list) and values and isinstance(values[0], list))
    ):
        return values

    # range가 범위를 포함하는지 확인
    range_pattern = (
        r"(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?"
    )
    match = re.match(range_pattern, sheet_range)

    if not match:
        return values

    # 단일 셀 또는 범위의 시작과 끝을 추출
    start_cell = match.group(1)
    end_cell = match.group(2)

    # 단일 셀인 경우 (범위가 없는 경우)
    if not end_cell:
        # 단일 셀에 중첩되지 않은 리스트가 입력된 경우 가공하지 않음
        return values

    # 열 방향 범위인지 확인 (예: A1:A10)
    start_col = re.search(r"[A-Z]+", start_cell).group(0)
    end_col = re.search(r"[A-Z]+", end_cell).group(0)

    start_row = re.search(r"[0-9]+", start_cell).group(0)
    end_row = re.search(r"[0-9]+", end_cell).group(0)

    # 열이 같고 행이 다르면 열 방향 범위
    if start_col == end_col and start_row != end_row:
        # 평면 리스트를 중첩 리스트로 변환
        return [[value] for value in values]

    return values


def json_loads(json_str: str) -> Union[dict, str]:
    if isinstance(json_str, (str, bytes)):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                return literal_eval(json_str)
            except (ValueError, SyntaxError):
                pass

    return json_str


def json_dumps(json_data: dict) -> str:
    return json.dumps(json_data, ensure_ascii=False)
"""
Excel automation
"""

import json
from ast import literal_eval
from typing import Optional, Union

import xlwings as xw

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.types import ExcelRange


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
def excel_get_values_from_active_sheet(sheet_range: Optional[ExcelRange] = None) -> str:
    """Get data from a specified range in the active sheet of an open Excel workbook.
    If no range is specified, gets data from the entire used range."""

    if sheet_range is None:
        data = xw.sheets.active.used_range.value
    else:
        data = xw.Range(sheet_range).value

    return json_dumps(data)


@mcp.tool()
def excel_get_values_from_sheet(book_name: str, sheet_name: str, sheet_range: Optional[ExcelRange] = None) -> str:
    """Get data from a specified range in a specific sheet of an open Excel workbook.
    If no range is specified, gets data from the entire used range."""

    sheet: xw.Sheet = xw.books[book_name].sheets[sheet_name]

    if sheet_range is None:
        data = sheet.used_range.value
    else:
        data = sheet.range(sheet_range).value

    return json_dumps(data)


@mcp.tool()
def excel_set_values_to_active_sheet(sheet_range: ExcelRange, json_values: Union[str, list]) -> None:
    """Write data to a specified range in the active sheet of an open Excel workbook.

    When adding values to consecutive cells, you only need to specify the starting cell coordinate,
    and the data will be populated according to the dimensions of the input.

    The dimensions of the input must match the expected format:
    - For rows, each row must have the same number of columns
    - For columns, each column must have the same number of rows

    Examples:
    - Write horizontally (1 row): sheet_range="A10" json_values='["v1", "v2", "v3"]'
    - Write vertically (1 column): sheet_range="A10" json_values='[["v1"], ["v2"], ["v3"]]'
    - Write multiple rows/columns: sheet_range="A10" json_values='[["v1", "v2"], ["v3", "v4"], ["v5", "v6"]]'
    """

    if sheet_range is None:
        range_ = xw.sheets.active.used_range
    else:
        range_ = xw.Range(sheet_range)

    range_.value = json_loads(json_values)


@mcp.tool()
def excel_set_values_to_sheet(
    book_name: str, sheet_name: str, sheet_range: ExcelRange, json_values: Union[str, list]
) -> None:
    """Write data to a specified range in a specific sheet of an open Excel workbook.

    When adding values to consecutive cells, you only need to specify the starting cell coordinate,
    and the data will be populated according to the dimensions of the input.

    The dimensions of the input must match the expected format:
    - For rows, each row must have the same number of columns
    - For columns, each column must have the same number of rows

    Examples:
    - Write horizontally (1 row): sheet_range="A10" json_values='["v1", "v2", "v3"]'
    - Write vertically (1 column): sheet_range="A10" json_values='[["v1"], ["v2"], ["v3"]]'
    - Write multiple rows/columns: sheet_range="A10" json_values='[["v1", "v2"], ["v3", "v4"], ["v5", "v6"]]'
    """

    sheet: xw.Sheet = xw.books[book_name].sheets[sheet_name]

    if sheet_range is None:
        range_ = sheet.used_range
    else:
        range_ = sheet.range(sheet_range)

    range_.value = json_loads(json_values)


def json_loads(json_str: str) -> Union[dict, str]:
    print("#### json_str :", repr(json_str))
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

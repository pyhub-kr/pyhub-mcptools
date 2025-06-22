"""Google Sheets MCP Tools"""

import logging
from typing import List, Literal, Optional, Union

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.google.sheets.client_async import get_async_client as get_client
from pyhub.mcptools.google.sheets.exceptions import GoogleSheetsError
from pyhub.mcptools.google.sheets.utils import ensure_2d_array, json_dumps, parse_sheet_range

logger = logging.getLogger(__name__)


def _get_enabled_gsheet_tools():
    """Check if Google Sheets tools are enabled"""
    return getattr(settings, "USE_GOOGLE_SHEETS", False)


# Spreadsheet management tools
@mcp.tool(
    description="""List Google Sheets spreadsheets.

Lists spreadsheets accessible by the authenticated Google account:
- Spreadsheets owned by the user
- Spreadsheets shared with the user
- Sorted by most recently modified

Returns:
- spreadsheets: List of spreadsheets
  - id: Spreadsheet ID
  - name: Spreadsheet name
  - url: Web URL to open the spreadsheet
  - createdTime: Creation timestamp
  - modifiedTime: Last modified timestamp""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_list_spreadsheets() -> str:
    """사용자가 접근 가능한 모든 Google Sheets 목록 반환"""
    client = get_client()
    spreadsheets = await client.list_spreadsheets()
    return json_dumps({"spreadsheets": spreadsheets})


@mcp.tool(
    description="""Search for spreadsheets by name.

Searches through accessible spreadsheets to find matches by name.
Supports partial matching and returns multiple results if found.

Args:
- search_term: Name or partial name to search for
- exact_match: Whether to match exactly (default: False)

Returns:
- matches: List of matching spreadsheets
  - id: Spreadsheet ID
  - name: Spreadsheet name
  - url: Web URL to open the spreadsheet
  - modifiedTime: Last modified timestamp""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_search_by_name(
    search_term: str = Field(description="Name or partial name to search for"),
    exact_match: bool = Field(default=False, description="Whether to match exactly"),
) -> str:
    """이름으로 스프레드시트 검색"""
    client = get_client()
    matches = await client.search_spreadsheets(search_term, exact_match)

    if not matches:
        return json_dumps({"matches": [], "message": f"No spreadsheets found matching '{search_term}'"})

    return json_dumps(
        {"matches": matches, "total": len(matches), "search_term": search_term, "exact_match": exact_match}
    )


@mcp.tool(
    description="""Create a new Google Sheets spreadsheet.

Creates an empty spreadsheet with one default sheet.

Args:
- name: Spreadsheet name

Returns:
- id: Created spreadsheet ID
- name: Spreadsheet name
- url: Web URL to open the spreadsheet""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_create_spreadsheet(name: str = Field(description="Spreadsheet name")) -> str:
    """새 스프레드시트 생성"""
    client = get_client()
    result = await client.create_spreadsheet(name)
    return json_dumps(result)


@mcp.tool(
    description="""Get Google Sheets spreadsheet information.

Returns information about all sheets in the spreadsheet.

Args:
- spreadsheet_id: Spreadsheet ID

Returns:
- id: Spreadsheet ID
- name: Spreadsheet name
- url: Web URL to open the spreadsheet
- sheets: List of sheets
  - id: Sheet ID
  - name: Sheet name
  - index: Sheet index
  - rowCount: Number of rows
  - columnCount: Number of columns""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_get_spreadsheet_info(spreadsheet_id: str = Field(description="Spreadsheet ID")) -> str:
    """스프레드시트 정보 조회"""
    client = get_client()
    info = await client.get_spreadsheet_info(spreadsheet_id)
    return json_dumps(info)


# Data manipulation tools
@mcp.tool(
    description="""Read data from a specified range in Google Sheets.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_range: Range to read (e.g., "Sheet1!A1:C10", "Sheet1" for entire sheet)
- expand_mode: How to expand from a single cell (optional)
  - "table": Detect contiguous data block (like Excel)
  - "down": Expand downward only
  - "right": Expand to the right only

Returns:
- values: Cell values as a 2D array
- range: The actual range that was read
- rowCount: Number of rows returned
- columnCount: Number of columns returned""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_get_values_from_range(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_range: str = Field(description="Range to read (e.g., 'Sheet1!A1:C10')"),
    expand_mode: Optional[Literal["table", "down", "right"]] = Field(
        default=None, description="Expand mode: 'table' for data block, 'down' for column, 'right' for row"
    ),
) -> str:
    """지정된 범위의 셀 값 읽기"""
    sheet_name, range_str = parse_sheet_range(sheet_range)
    client = get_client()

    # expand_mode가 있으면 단일 셀로 시작해야 함
    if expand_mode and range_str and ":" in range_str:
        # 범위가 지정된 경우 시작 셀만 사용
        range_str = range_str.split(":")[0]

    values = await client.get_values(spreadsheet_id, sheet_name, range_str, expand_mode)

    return json_dumps(
        {
            "values": values,
            "range": sheet_range,
            "rowCount": len(values),
            "columnCount": len(values[0]) if values else 0,
            "expand_mode": expand_mode,
        }
    )


@mcp.tool(
    description="""Write data to a specified range in Google Sheets.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_range: Range to write (e.g., "Sheet1!A1:C10")
- values: Data to write (2D array or 1D array)

Returns:
- updatedCells: Number of cells updated
- updatedRows: Number of rows updated
- updatedColumns: Number of columns updated
- updatedRange: The actual range that was updated""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_set_values_to_range(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_range: str = Field(description="Range to write (e.g., 'Sheet1!A1:C10')"),
    values: List[List[Union[str, int, float]]] = Field(description="Data to write (2D array)"),
) -> str:
    """지정된 범위에 값 설정"""
    sheet_name, range_str = parse_sheet_range(sheet_range)
    if not range_str:
        raise GoogleSheetsError("Range must be specified (e.g., 'Sheet1!A1:C10')")

    # 2차원 배열로 변환
    normalized_values = ensure_2d_array(values)

    client = get_client()
    result = await client.set_values(spreadsheet_id, sheet_name, range_str, normalized_values)
    return json_dumps(result)


@mcp.tool(
    description="""Clear data from a specified range in Google Sheets.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_range: Range to clear (e.g., "Sheet1!A1:C10")

Returns:
- clearedRange: The range that was cleared""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_clear_range(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_range: str = Field(description="Range to clear (e.g., 'Sheet1!A1:C10')"),
) -> str:
    """지정된 범위의 값 삭제"""
    sheet_name, range_str = parse_sheet_range(sheet_range)
    if not range_str:
        raise GoogleSheetsError("Range must be specified (e.g., 'Sheet1!A1:C10')")

    client = get_client()
    result = await client.clear_values(spreadsheet_id, sheet_name, range_str)
    return json_dumps(result)


# Sheet management tools
@mcp.tool(
    description="""Add a new sheet to a Google Sheets spreadsheet.

Args:
- spreadsheet_id: Spreadsheet ID
- name: New sheet name
- index: Sheet position (optional, defaults to last)

Returns:
- id: New sheet ID
- name: Sheet name
- index: Sheet position""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_add_sheet(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    name: str = Field(description="New sheet name"),
    index: Optional[int] = Field(default=None, description="Sheet position (optional)"),
) -> str:
    """새 시트 추가"""
    client = get_client()
    result = await client.add_sheet(spreadsheet_id, name, index)
    return json_dumps(result)


@mcp.tool(
    description="""Delete a sheet from a Google Sheets spreadsheet.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_name: Sheet name to delete

Warning: Deleted sheets cannot be recovered.""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_delete_sheet(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_name: str = Field(description="Sheet name to delete"),
) -> str:
    """시트 삭제"""
    client = get_client()
    await client.delete_sheet(spreadsheet_id, sheet_name)
    return json_dumps({"success": True, "message": f"Sheet '{sheet_name}' has been deleted."})


@mcp.tool(
    description="""Rename a sheet in a Google Sheets spreadsheet.

Args:
- spreadsheet_id: Spreadsheet ID
- sheet_name: Current sheet name
- new_name: New sheet name

Returns:
- id: Sheet ID
- name: New sheet name
- index: Sheet position""",
    enabled=lambda: _get_enabled_gsheet_tools(),
)
async def gsheet_rename_sheet(
    spreadsheet_id: str = Field(description="Spreadsheet ID"),
    sheet_name: str = Field(description="Current sheet name"),
    new_name: str = Field(description="New sheet name"),
) -> str:
    """시트 이름 변경"""
    client = get_client()
    result = await client.rename_sheet(spreadsheet_id, sheet_name, new_name)
    return json_dumps(result)

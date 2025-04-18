from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import (
    ExcelExpandMode,
)
from pyhub.mcptools.excel.utils import get_range


@mcp.tool()
@macos_excel_request_permission
def excel_convert_to_table(
    sheet_range: str = Field(
        description="Excel range containing the source data for the chart",
        examples=["A1:B10", "Sheet1!A1:C5", "Data!A1:D20"],
    ),
    book_name: str = Field(
        default="",
        description="Name of workbook containing source data. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: str = Field(
        default="",
        description="Name of sheet containing source data. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
    expand_mode: str = Field(
        default=ExcelExpandMode.get_none_value(),
        description=ExcelExpandMode.get_description("Mode for automatically expanding the selection range"),
    ),
    table_name: str = Field(default="", description="Name of workbook containing source data. Optional."),
    has_headers: str = Field(
        default="true",
        examples=["true", "false", "guess"],
    ),
    table_style_name: str = Field(
        default="TableStyleMedium2",
        description="""
            Possible strings: 'TableStyleLightN' (where N is 1-21), 'TableStyleMediumN' (where N is 1-28), 'TableStyleDarkN' (where N is 1-11)
        """,
        examples=["TableStyleMedium2"],
    ),
) -> str:
    """
    Convert Excel range to table. Windows only.
    """

    if OS.current_is_windows() is False:
        return "Error: This feature is only supported on Windows."

    has_headers = has_headers.lower().strip()
    if has_headers == "guess":
        has_headers = "guess"
    elif has_headers.startswith("f"):
        has_headers = False
    else:
        has_headers = True

    source_range_ = get_range(
        sheet_range=sheet_range,
        book_name=book_name,
        sheet_name=sheet_name,
        expand_mode=expand_mode,
    )

    current_sheet = source_range_.sheet

    # https://docs.xlwings.org/en/stable/api/tables.html
    table = current_sheet.tables.add(
        source=source_range_.expand("table"),
        name=table_name or None,
        has_headers=has_headers,
        table_style_name=table_style_name,
    )

    # TODO: 이미 테이블일 때, 다시 테이블 변환은 안 됩니다. 아래 코드로 테이블을 해제시킬 수 있음.
    # current_sheet.api.ListObjects(table_name).UnList()

    return f"Table(name='{table.name}') created successfully."

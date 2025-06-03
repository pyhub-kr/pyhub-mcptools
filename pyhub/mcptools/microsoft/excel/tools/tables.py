import asyncio

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.microsoft.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.microsoft.excel.forms import PivotTableCreateForm
from pyhub.mcptools.microsoft.excel.types import ExcelExpandMode
from pyhub.mcptools.microsoft.excel.utils import (
    get_range,
    get_sheet,
    json_dumps,
)
from pyhub.mcptools.microsoft.excel.utils.tables import PivotTable

# Default timeout for Excel operations
EXCEL_DEFAULT_TIMEOUT = 60

# TODO: macOS 지원 추가 : macOS에서 xlwings 활용 테이블 생성 시에 오류 발생


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT, enabled=OS.current_is_windows())
async def excel_convert_to_table(
    sheet_range: str = Field(
        description="Excel range to convert to table",
        examples=["A1:D10", "Sheet1!B2:F20"],
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
        description=ExcelExpandMode.get_description("Mode for automatically expanding the selection range"),
    ),
    table_name: str = Field(
        default="",
        description="Name for the table. Auto-generated if not provided.",
        examples=["SalesTable", "CustomerData"],
    ),
    has_headers: str = Field(
        default="true",
        description="Whether first row contains headers (true/false/guess)",
        examples=["true", "false", "guess"],
    ),
    table_style_name: str = Field(
        default="TableStyleMedium2",
        description="Excel table style name",
        examples=["TableStyleLight1", "TableStyleMedium2", "TableStyleDark1"],
    ),
) -> str:
    """Convert an Excel range to a formatted table (Windows only).

    Tables provide structured references, automatic formatting, and filtering.
    Note: This feature is currently only available on Windows due to xlwings limitations.

    Returns:
        str: Success message
    """

    @macos_excel_request_permission
    def _convert_to_table():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            # Get the range
            range_ = get_range(
                sheet_range=sheet_range,
                book_name=book_name,
                sheet_name=sheet_name,
                expand_mode=expand_mode,
            )

            # Expand to table if needed
            if expand_mode == ExcelExpandMode.TABLE.value:
                range_ = range_.expand("table")

            # Convert to table
            sheet = range_.sheet
            has_headers_bool = None if has_headers == "guess" else (has_headers.lower() == "true")

            table = sheet.tables.add(
                source_range=range_,
                name=table_name or None,
                has_headers=has_headers_bool,
                table_style_name=table_style_name,
            )

            return f"Successfully converted range to table: {table.name}"
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_convert_to_table)


# TODO: table 목록/내역 반환


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_add_pivot_table(
    source_sheet_range: str = Field(
        description="Data source range for pivot table",
        examples=["A1:E100", "Sheet1!A1:G50"],
    ),
    dest_sheet_range: str = Field(
        description="Top-left cell where pivot table will be placed",
        examples=["H1", "Sheet2!A1"],
    ),
    source_book_name: str = Field(
        default="",
        description="Source workbook name. Optional.",
        examples=["Sales.xlsx"],
    ),
    source_sheet_name: str = Field(
        default="",
        description="Source sheet name. Optional.",
        examples=["RawData"],
    ),
    dest_book_name: str = Field(
        default="",
        description="Destination workbook name. Optional.",
        examples=["Report.xlsx"],
    ),
    dest_sheet_name: str = Field(
        default="",
        description="Destination sheet name. Optional.",
        examples=["Summary"],
    ),
    expand_mode: str = Field(
        default=ExcelExpandMode.get_none_value(),
        description=ExcelExpandMode.get_description("Mode for expanding source data range"),
    ),
    row_field_names: str = Field(
        description="Comma-separated field names for rows",
        examples=["Category,Product", "Region"],
    ),
    column_field_names: str = Field(
        default="",
        description="Comma-separated field names for columns. Optional.",
        examples=["Month", "Quarter,Year"],
    ),
    page_field_names: str = Field(
        default="",
        description="Comma-separated field names for filters. Optional.",
        examples=["Region", "Category,Status"],
    ),
    value_fields: str = Field(
        description="Pipe-separated value fields with aggregation (field:function)",
        examples=["Sales:sum", "Quantity:sum|Revenue:average"],
    ),
    pivot_table_name: str = Field(
        default="",
        description="Name for the pivot table. Auto-generated if not provided.",
        examples=["SalesSummary", "RegionalAnalysis"],
    ),
) -> str:
    """Create a pivot table from source data.

    Pivot tables summarize and analyze data with flexible row/column/value configurations.
    Value fields format: 'FieldName:AggregateFunction' separated by pipes (|)
    Aggregate functions: sum, count, average, max, min, product, stdev, stdevp, var, varp

    Returns:
        str: Success message with pivot table name
    """

    @macos_excel_request_permission
    def _add_pivot_table():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            # Get source and destination ranges
            source_range = get_range(
                sheet_range=source_sheet_range,
                book_name=source_book_name,
                sheet_name=source_sheet_name,
                expand_mode=expand_mode,
            )
            dest_range = get_range(
                sheet_range=dest_sheet_range,
                book_name=dest_book_name,
                sheet_name=dest_sheet_name,
            )

            # Use the form for validation and creation
            form = PivotTableCreateForm(
                data={
                    "row_field_names": row_field_names,
                    "column_field_names": column_field_names,
                    "page_field_names": page_field_names,
                    "value_fields": value_fields,
                    "pivot_table_name": pivot_table_name,
                },
                source_range=source_range,
                dest_range=dest_range,
            )

            if not form.is_valid():
                return f"Validation error: {form.errors}"

            result = form.save()
            return result
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_add_pivot_table)


# Note: excel_get_pivot_tables is now part of excel_get_info tool
# Keeping this for backward compatibility if needed
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_get_pivot_tables(
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
    """List all pivot tables in the specified sheet.

    Returns:
        str: JSON list of pivot table information
    """

    @macos_excel_request_permission
    def _get_pivot_tables():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
            return json_dumps(PivotTable.list(sheet))
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_get_pivot_tables)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_remove_pivot_tables(
    remove_all: bool = Field(
        default=False,
        description="Remove all pivot tables in the sheet",
    ),
    pivot_table_names: str = Field(
        default="",
        description="Comma-separated names of pivot tables to remove",
        examples=["PivotTable1", "Sales,Revenue,Costs"],
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
    """Remove pivot tables from a sheet.

    Either remove all pivot tables or specific ones by name.
    Must specify either remove_all=True or provide pivot_table_names.

    Returns:
        str: Success or error message
    """

    @macos_excel_request_permission
    def _remove_pivot_tables():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

            if remove_all:
                result = PivotTable.remove_all(sheet)
            elif pivot_table_names:
                names = [name.strip() for name in pivot_table_names.split(",")]
                results = []
                for name in names:
                    result = PivotTable.remove(sheet, name)
                    results.append(result)
                result = "; ".join(results)
            else:
                result = "Specify either remove_all=True or provide pivot_table_names"

            return result
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_remove_pivot_tables)

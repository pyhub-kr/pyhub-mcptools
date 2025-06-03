import asyncio

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.microsoft.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.microsoft.excel.types import ExcelChartType
from pyhub.mcptools.microsoft.excel.utils import (
    get_range,
    get_sheet,
    json_dumps,
)

# Default timeout for Excel operations
EXCEL_DEFAULT_TIMEOUT = 60

# Note: excel_get_charts is now part of excel_get_info tool
# Keeping this for backward compatibility if needed
@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_get_charts(
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
    """Get all charts in the specified Excel sheet.

    Returns:
        str: JSON list with chart properties: name, position, size, index
    """

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

    return await asyncio.to_thread(_get_charts)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_add_chart(
    source_sheet_range: str = Field(
        description="Excel range containing chart data",
        examples=["A1:B10", "Sheet1!A1:C20"],
    ),
    dest_sheet_range: str = Field(
        description="Top-left cell where chart will be placed",
        examples=["D2", "Sheet2!E5"],
    ),
    source_book_name: str = Field(
        default="",
        description="Source workbook name. Optional.",
        examples=["Sales.xlsx"],
    ),
    source_sheet_name: str = Field(
        default="",
        description="Source sheet name. Optional.",
        examples=["Data"],
    ),
    dest_book_name: str = Field(
        default="",
        description="Destination workbook name. Optional.",
        examples=["Report.xlsx"],
    ),
    dest_sheet_name: str = Field(
        default="",
        description="Destination sheet name. Optional.",
        examples=["Charts"],
    ),
    chart_type: str = Field(
        default=ExcelChartType.LINE.value,
        description="Type of chart to create",
        examples=[t.value for t in ExcelChartType],
    ),
    name: str = Field(
        default="",
        description="Name for the chart. Auto-generated if not provided.",
        examples=["SalesChart", "TrendLine2023"],
    ),
) -> str:
    """Add a chart to an Excel sheet.

    Creates a chart using data from source range and places it at destination.
    Supports creating charts across different sheets or workbooks.

    Returns:
        str: Name of the created chart
    """

    @macos_excel_request_permission
    def _add_chart():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            # Get source and destination ranges
            source_range = get_range(
                sheet_range=source_sheet_range,
                book_name=source_book_name,
                sheet_name=source_sheet_name,
            )
            dest_range = get_range(
                sheet_range=dest_sheet_range,
                book_name=dest_book_name,
                sheet_name=dest_sheet_name,
            )

            # Create chart
            dest_sheet = dest_range.sheet
            chart = dest_sheet.charts.add(
                left=dest_range.left,
                top=dest_range.top,
                width=375,  # Default width
                height=225,  # Default height
            )

            # Set chart type and source data
            chart.chart_type = chart_type
            chart.set_source_data(source_range)

            # Set name if provided
            if name:
                chart.name = name

            return chart.name
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_add_chart)


@mcp.tool(timeout=EXCEL_DEFAULT_TIMEOUT)
async def excel_set_chart_props(
    name: str = Field(
        description="Name of the chart to modify",
        examples=["Chart 1", "SalesChart"],
    ),
    chart_book_name: str = Field(
        default="",
        description="Workbook containing the chart. Optional.",
        examples=["Report.xlsx"],
    ),
    chart_sheet_name: str = Field(
        default="",
        description="Sheet containing the chart. Optional.",
        examples=["Dashboard"],
    ),
    new_name: str = Field(
        default="",
        description="New name for the chart. Optional.",
        examples=["UpdatedChart"],
    ),
    new_chart_type: str = Field(
        default="",
        description="New chart type. Optional.",
        examples=[t.value for t in ExcelChartType],
    ),
    source_sheet_range: str = Field(
        default="",
        description="New data source range. Optional.",
        examples=["A1:C20"],
    ),
    source_book_name: str = Field(
        default="",
        description="New source workbook. Optional.",
        examples=["NewData.xlsx"],
    ),
    source_sheet_name: str = Field(
        default="",
        description="New source sheet. Optional.",
        examples=["Sheet2"],
    ),
    dest_sheet_range: str = Field(
        default="",
        description="New position/size (uses top-left cell and optionally bottom-right for size). Optional.",
        examples=["E5", "E5:J15"],
    ),
    dest_book_name: str = Field(
        default="",
        description="Destination workbook for moving chart. Optional.",
        examples=["Report.xlsx"],
    ),
    dest_sheet_name: str = Field(
        default="",
        description="Destination sheet for moving chart. Optional.",
        examples=["Charts"],
    ),
) -> str:
    """Modify properties of an existing chart.

    Can change name, type, data source, position, and size.
    All modifications are optional - only specified properties will be changed.

    Returns:
        str: Name of the modified chart
    """

    @macos_excel_request_permission
    def _set_chart_props():
        from pyhub.mcptools.microsoft.excel.utils import cleanup_excel_com

        try:
            # Get the chart
            sheet = get_sheet(book_name=chart_book_name, sheet_name=chart_sheet_name)
            chart = sheet.charts[name]

            # Update name
            if new_name:
                chart.name = new_name

            # Update chart type
            if new_chart_type:
                chart.chart_type = new_chart_type

            # Update data source
            if source_sheet_range:
                source_range = get_range(
                    sheet_range=source_sheet_range,
                    book_name=source_book_name,
                    sheet_name=source_sheet_name,
                )
                chart.set_source_data(source_range)

            # Update position/size
            if dest_sheet_range:
                dest_range = get_range(
                    sheet_range=dest_sheet_range,
                    book_name=dest_book_name,
                    sheet_name=dest_sheet_name,
                )

                # Set position
                chart.left = dest_range.left
                chart.top = dest_range.top

                # Set size if range spans multiple cells
                if dest_range.count > 1:
                    chart.width = dest_range.width
                    chart.height = dest_range.height

            return chart.name
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_set_chart_props)

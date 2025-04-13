from typing import Optional

from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import ExcelChartType, ExcelRange
from pyhub.mcptools.excel.utils import get_range, get_sheet, json_dumps


@mcp.tool()
@macos_excel_request_permission
def excel_get_charts(
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
    """Get a list of all charts in the specified Excel sheet.

    Retrieves information about all charts in a specified Excel sheet. By default uses the active workbook
    and sheet if no specific book_name or sheet_name is provided.

    Returns:
        str: A JSON string containing a list of dictionaries with chart information.
             Each dictionary has the following keys:
             - name: The name of the chart
             - left: The left position of the chart
             - top: The top position of the chart
             - width: The width of the chart
             - height: The height of the chart
             - index: Zero-based index of the chart

    Examples:
        >>> excel_get_charts()  # Get charts from active sheet
        >>> excel_get_charts("Sales.xlsx")  # Get charts from specific workbook
        >>> excel_get_charts("Report.xlsx", "Sheet2")  # Get charts from specific sheet
    """
    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
    return json_dumps(
        [
            {
                "name": chart.name,
                "left": chart.left,
                "top": chart.top,
                "width": chart.width,
                "height": chart.height,
                "index": idx,
            }
            for idx, chart in enumerate(sheet.charts)
        ]
    )


@mcp.tool()
@macos_excel_request_permission
def excel_add_chart(
    source_sheet_range: ExcelRange = Field(
        description="Excel range containing the source data for the chart",
        examples=["A1:B10", "Sheet1!A1:C5", "Data!A1:D20"],
    ),
    dest_sheet_range: ExcelRange = Field(
        description="Excel range where the chart should be placed",
        examples=["D1:E10", "Sheet1!G1:H10", "Chart!A1:C10"],
    ),
    source_book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook containing source data. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    source_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet containing source data. If None, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
    dest_book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook where chart will be created. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    dest_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet where chart will be created. If None, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
    type: ExcelChartType = Field(
        default=ExcelChartType.LINE,
        description="Type of chart to create.",
        examples=["LINE", "BAR", "PIE", "COLUMN"],
    ),
    name: Optional[str] = Field(
        default=None,
        description="Name to assign to the chart. If None, Excel assigns a default name.",
        examples=["SalesChart", "RevenueGraph", "TrendAnalysis"],
    ),
) -> str:
    """Add a new chart to an Excel sheet using data from a specified range.

    Creates a new chart in the destination range using data from the source range. The chart can be
    customized with different chart types and can be named for easier reference.

    Chart Behavior:
        - The destination range determines the size and position of the chart
        - Chart types are defined in the ExcelChartType enum
        - Source data should be properly formatted for the chosen chart type
        - If source and destination are in different workbooks/sheets, both must be open

    Returns:
        str: The name of the created chart.

    Examples:
        >>> excel_add_chart("A1:B10", "D1:E10")  # Basic line chart
        >>> excel_add_chart("Sheet1!A1:C5", "D1:F10", type=ExcelChartType.BAR)  # Bar chart
        >>> excel_add_chart("Data!A1:B10", "Chart!C1:D10", name="SalesChart")  # Named chart
        >>> excel_add_chart("A1:D5", "E1:H10", source_sheet_name="Data", dest_sheet_name="Charts")  # Different sheets
    """
    source_range_ = get_range(sheet_range=source_sheet_range, book_name=source_book_name, sheet_name=source_sheet_name)
    dest_range_ = get_range(sheet_range=dest_sheet_range, book_name=dest_book_name, sheet_name=dest_sheet_name)

    dest_sheet = dest_range_.sheet

    chart = dest_sheet.charts.add(
        left=dest_range_.left,
        top=dest_range_.top,
        width=dest_range_.width,
        height=dest_range_.height,
    )
    chart.chart_type = type.value
    chart.set_source_data(source_range_)
    if name is not None:
        chart.name = name

    return chart.name


@mcp.tool()
@macos_excel_request_permission
def excel_set_chart_props(
    name: Optional[str] = Field(
        default=None,
        description="The name of the chart to modify.",
        examples=["SalesChart", "RevenueGraph"],
    ),
    index: Optional[int] = Field(
        default=None,
        description="The zero-based index of the chart to modify.",
        examples=[0, 1, 2],
    ),
    chart_book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook containing the chart. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    chart_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet containing the chart. If None, uses active sheet.",
        examples=["Sheet1", "Charts"],
    ),
    new_name: Optional[str] = Field(
        default=None,
        description="New name to assign to the chart. If None, name remains unchanged.",
        examples=["UpdatedSalesChart", "Q2Revenue"],
    ),
    new_chart_type: Optional[ExcelChartType] = Field(
        default=None,
        description="New chart type to set. If None, chart type remains unchanged.",
        examples=["LINE", "BAR", "PIE", "COLUMN"],
    ),
    source_sheet_range: Optional[ExcelRange] = Field(
        default=None,
        description="New Excel range for chart data. If None, source data remains unchanged.",
        examples=["A1:B10", "Sheet1!A1:C5", "Data!A1:D20"],
    ),
    source_book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook containing new source data. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    source_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet containing new source data. If None, uses active sheet.",
        examples=["Sheet1", "Data"],
    ),
    dest_sheet_range: Optional[ExcelRange] = Field(
        default=None,
        description="New Excel range for chart position and size. If None, position remains unchanged.",
        examples=["D1:E10", "Sheet1!G1:H10", "Chart!A1:C10"],
    ),
    dest_book_name: Optional[str] = Field(
        default=None,
        description="Name of workbook for destination. If None, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    dest_sheet_name: Optional[str] = Field(
        default=None,
        description="Name of sheet for destination. If None, uses active sheet.",
        examples=["Sheet1", "Charts"],
    ),
) -> str:
    """Update properties of an existing chart in an Excel sheet.

    Modifies properties of a specified chart, such as its name, source data range, or position.
    The chart can be identified by its name or index, and the function allows updating the chart name,
    source data range, and/or the chart's position and size.

    Chart Update Rules:
        - At least one of new_name, source_sheet_range, dest_sheet_range,
          or new_chart_type must be provided to make any changes
        - The chart must exist in the specified workbook/sheet
        - If changing source data from a different workbook/sheet, both must be open
        - Source data should be properly formatted for the chart type
        - The dest_sheet_range determines the new position and size of the chart if provided

    Returns:
        str: The name of the chart after modifications (either original name or new name if changed).

    Examples:
        >>> excel_set_chart_props(name="SalesChart", new_name="Q2Sales")  # Rename chart
        >>> excel_set_chart_props(index=0, new_chart_type=ExcelChartType.BAR)  # Change type
        >>> excel_set_chart_props("RevenueChart", source_sheet_range="A1:B20")  # Update data
        >>> excel_set_chart_props("TrendChart", dest_sheet_range="E1:F10")  # Move chart
    """
    if name is None and index is None:
        raise ValueError("Either name or index must be provided")
    if name is not None and index is not None:
        raise ValueError("Only one of name or index should be provided")

    chart_sheet = get_sheet(book_name=chart_book_name, sheet_name=chart_sheet_name)
    if name is not None:
        chart = chart_sheet.charts[name]
    else:
        chart = chart_sheet.charts[index]

    if new_name is not None:
        chart.name = new_name

    if new_chart_type is not None:
        chart.chart_type = new_chart_type.value

    if source_sheet_range is not None:
        source_range_ = get_range(
            sheet_range=source_sheet_range,
            book_name=source_book_name,
            sheet_name=source_sheet_name,
        )
        chart.set_source_data(source_range_)

    if dest_sheet_range is not None:
        dest_range_ = get_range(sheet_range=dest_sheet_range, book_name=dest_book_name, sheet_name=dest_sheet_name)
        chart.left = dest_range_.left
        chart.top = dest_range_.top
        chart.width = dest_range_.width
        chart.height = dest_range_.height

    return chart.name

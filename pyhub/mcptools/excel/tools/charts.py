from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import ExcelChartType
from pyhub.mcptools.excel.utils import get_range, get_sheet, json_dumps


@mcp.tool()
@macos_excel_request_permission
def excel_get_charts(
    book_name: str = Field(
        default="",
        description="Name of workbook to use. If not specified, uses active workbook.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: str = Field(
        default="",
        description="Name of sheet to use. If not specified, uses active sheet.",
        examples=["Sheet1", "Sales2023"],
    ),
) -> str:
    """Get a list of all charts in the specified Excel sheet.

    Retrieves chart information from specified sheet. Uses active workbook/sheet if not specified.

    Returns:
        str: JSON string containing chart information list:
            - name: Chart name
            - left: Left position
            - top: Top position
            - width: Width
            - height: Height
            - index: Zero-based index

    Examples:
        >>> excel_get_charts()  # Active sheet
        >>> excel_get_charts("Sales.xlsx")  # Specific workbook
        >>> excel_get_charts("Report.xlsx", "Sheet2")  # Specific sheet
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
    source_sheet_range: str = Field(
        description="Excel range containing the source data for the chart",
        examples=["A1:B10", "Sheet1!A1:C5", "Data!A1:D20"],
    ),
    dest_sheet_range: str = Field(
        description="Excel range where the chart should be placed",
        examples=["D1:E10", "Sheet1!G1:H10", "Chart!A1:C10"],
    ),
    source_book_name: str = Field(
        default="",
        description="Name of workbook containing source data. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    source_sheet_name: str = Field(
        default="",
        description="Name of sheet containing source data. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
    dest_book_name: str = Field(
        default="",
        description="Name of workbook where chart will be created. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    dest_sheet_name: str = Field(
        default="",
        description="Name of sheet where chart will be created. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
    # FIXME: (확인 요망) TextChoices로 생성한 타입에 대해서 Optional을 지정하지 않으면, Claude Desktop이 죽습니다.
    # 로그도 남겨지지 않아 이유를 알 수 없습니다.
    chart_type: str = Field(
        default=ExcelChartType.LINE.value,
        description=ExcelChartType.get_description("Type of chart to create"),
    ),
    name: str = Field(
        default="",
        description="Name to assign to the chart. Optional.",
        examples=["SalesChart", "RevenueGraph", "TrendAnalysis"],
    ),
) -> str:
    """Add a new chart to an Excel sheet using data from a specified range.

    Creates a chart in the destination range using data from the source range.
    Supports different chart types and custom naming.

    Best Practices:
        1. Range Selection:
           - Use excel_find_data_ranges() to identify suitable empty areas
           - Avoid overlapping with existing content

        2. Data Protection:
           - Check for existing content in destination range
           - Confirm before overwriting existing content

    Chart Behavior:
        - Destination range determines chart size and position
        - Chart types are defined in ExcelChartType enum
        - Source data must match chosen chart type format
        - Cross-workbook operations require both workbooks to be open

    Returns:
        str: Name of the created chart

    Examples:
        >>> excel_add_chart("A1:B10", "D1:E10")  # Basic line chart
        >>> excel_add_chart("Sheet1!A1:C5", "D1:F10", chart_type="bar")  # Bar chart
        >>> excel_add_chart("Data!A1:B10", "Chart!C1:D10", name="SalesChart")  # Named chart
    """

    source_range_ = get_range(
        sheet_range=source_sheet_range,
        book_name=source_book_name,
        sheet_name=source_sheet_name,
    )
    dest_range_ = get_range(
        sheet_range=dest_sheet_range,
        book_name=dest_book_name,
        sheet_name=dest_sheet_name,
    )

    dest_sheet = dest_range_.sheet

    chart = dest_sheet.charts.add(
        left=dest_range_.left,
        top=dest_range_.top,
        width=dest_range_.width,
        height=dest_range_.height,
    )
    chart.chart_type = chart_type
    chart.set_source_data(source_range_)
    if name is not None:
        chart.name = name

    return chart.name


@mcp.tool()
@macos_excel_request_permission
def excel_set_chart_props(
    name: str = Field(
        description="The name of the chart to modify.",
        examples=["SalesChart", "RevenueGraph"],
    ),
    chart_book_name: str = Field(
        default="",
        description="Name of workbook containing the chart. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    chart_sheet_name: str = Field(
        default="",
        description="Name of sheet containing the chart. Optional.",
        examples=["Sheet1", "Charts"],
    ),
    new_name: str = Field(
        default="",
        description="New name to assign to the chart. Optional.",
        examples=["UpdatedSalesChart", "Q2Revenue"],
    ),
    new_chart_type: str = Field(
        default=ExcelChartType.get_none_value(),
        description=ExcelChartType.get_description(),
    ),
    source_sheet_range: str = Field(
        default="",
        description="New Excel range for chart data. Optional.",
        examples=["A1:B10", "Sheet1!A1:C5", "Data!A1:D20"],
    ),
    source_book_name: str = Field(
        default="",
        description="Name of workbook containing new source data. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    source_sheet_name: str = Field(
        default="",
        description="Name of sheet containing new source data. Optional.",
        examples=["Sheet1", "Data"],
    ),
    dest_sheet_range: str = Field(
        default="",
        description="New Excel range for chart position and size. Optional.",
        examples=["D1:E10", "Sheet1!G1:H10", "Chart!A1:C10"],
    ),
    dest_book_name: str = Field(
        default="",
        description="Name of workbook for destination. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    dest_sheet_name: str = Field(
        default="",
        description="Name of sheet for destination. Optional.",
        examples=["Sheet1", "Charts"],
    ),
) -> str:
    """Update properties of an existing chart in an Excel sheet.

    Modifies chart properties including name, source data range, chart type, and position/size.

    Best Practices:
        1. Range Changes:
           - Use excel_find_data_ranges() to identify suitable empty areas
           - Avoid overlapping with existing content

        2. Data Protection:
           - Check for existing content in destination range
           - Confirm before overwriting existing content

        3. Source Data Changes:
           - Verify data format compatibility
           - Ensure data is appropriate for chart type

    Rules:
        - Requires at least one change parameter (new_name, source_sheet_range, etc.)
        - Chart must exist in specified workbook/sheet
        - Both source and destination workbooks must be open for cross-workbook changes
        - dest_sheet_range controls chart position and size

    Returns:
        str: Chart name after modifications

    Examples:
        >>> excel_set_chart_props(name="SalesChart", new_name="Q2Sales")  # Rename
        >>> excel_set_chart_props(name="RevenueChart", new_chart_type="bar")  # Change type
        >>> excel_set_chart_props("TrendChart", source_sheet_range="A1:B20")  # Update data
        >>> excel_set_chart_props("TrendChart", dest_sheet_range="E1:F10")  # Move chart
    """

    chart_sheet = get_sheet(book_name=chart_book_name, sheet_name=chart_sheet_name)
    chart = chart_sheet.charts[name]

    if new_name:
        chart.name = new_name

    if new_chart_type:
        chart.chart_type = new_chart_type

    if source_sheet_range:
        source_range_ = get_range(
            sheet_range=source_sheet_range,
            book_name=source_book_name,
            sheet_name=source_sheet_name,
        )
        chart.set_source_data(source_range_)

    if dest_sheet_range:
        dest_range_ = get_range(sheet_range=dest_sheet_range, book_name=dest_book_name, sheet_name=dest_sheet_name)
        chart.left = dest_range_.left
        chart.top = dest_range_.top
        chart.width = dest_range_.width
        chart.height = dest_range_.height

    return chart.name

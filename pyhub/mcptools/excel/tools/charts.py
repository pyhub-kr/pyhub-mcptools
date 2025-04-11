from typing import Optional

from pyhub.mcptools import mcp
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import ExcelChartType, ExcelRange
from pyhub.mcptools.excel.utils import get_range, get_sheet, json_dumps


@mcp.tool()
@macos_excel_request_permission
def excel_get_charts(
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> str:
    """Get a list of all charts in the specified Excel sheet.

    Retrieves information about all charts in a specified Excel sheet. By default uses the active workbook
    and sheet if no specific book_name or sheet_name is provided.

    Parameters:
        book_name (Optional[str]): Name of workbook to use. If None, uses active workbook.
        sheet_name (Optional[str]): Name of sheet to use. If None, uses active sheet.

    Returns:
        str: A JSON string containing a list of dictionaries with chart information.
             Each dictionary has the following keys:
             - name: The name of the chart
             - left: The left position of the chart
             - top: The top position of the chart
             - width: The width of the chart
             - height: The height of the chart
             - index: Zero-based index of the chart (can be used for chart lookup along with name)

    Note:
        Charts can be looked up using either their name or index in other chart-related functions.
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
    source_sheet_range: ExcelRange,
    dest_sheet_range: ExcelRange,
    source_book_name: Optional[str] = None,
    source_sheet_name: Optional[str] = None,
    dest_book_name: Optional[str] = None,
    dest_sheet_name: Optional[str] = None,
    type: ExcelChartType = ExcelChartType.LINE,
    name: Optional[str] = None,
) -> str:
    """Add a new chart to an Excel sheet using data from a specified range.

    Creates a new chart in the destination range using data from the source range. The chart can be
    customized with different chart types and can be named for easier reference.

    Parameters:
        source_sheet_range (ExcelRange): Excel range containing the source data for the chart (e.g., "A1:B10").
        dest_sheet_range (ExcelRange): Excel range where the chart should be placed (e.g., "D1:E10").
        source_book_name (Optional[str]): Name of workbook containing source data. If None, uses active workbook.
        source_sheet_name (Optional[str]): Name of sheet containing source data. If None, uses active sheet.
        dest_book_name (Optional[str]): Name of workbook where chart will be created. If None, uses active workbook.
        dest_sheet_name (Optional[str]): Name of sheet where chart will be created. If None, uses active sheet.
        type (ExcelChartType): Type of chart to create. Defaults to LINE chart.
        name (Optional[str]): Name to assign to the chart. If None, Excel assigns a default name.

    Returns:
        str: The name of the created chart.

    Note:
        - The destination range determines the size and position of the chart.
        - Chart types are defined in the ExcelChartType enum.
        - The source data should be properly formatted for the chosen chart type.
        - If source and destination are in different workbooks/sheets, both must be open.
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
    name: Optional[str] = None,
    index: Optional[int] = None,
    chart_book_name: Optional[str] = None,
    chart_sheet_name: Optional[str] = None,
    new_name: Optional[str] = None,
    new_chart_type: Optional[ExcelChartType] = None,
    source_sheet_range: Optional[ExcelRange] = None,
    source_book_name: Optional[str] = None,
    source_sheet_name: Optional[str] = None,
    dest_sheet_range: Optional[ExcelRange] = None,
    dest_book_name: Optional[str] = None,
    dest_sheet_name: Optional[str] = None,
) -> str:
    """Update properties of an existing chart in an Excel sheet.

    Modifies properties of a specified chart, such as its name, source data range, or position.
    The chart can be identified by its name or index, and the function allows updating the chart name,
    source data range, and/or the chart's position and size.

    Parameters:
        name (Optional[str]): The name of the chart to modify.
        index (Optional[int]): The zero-based index of the chart to modify.
        chart_book_name (Optional[str]): Name of workbook containing the chart. If None, uses active workbook.
        chart_sheet_name (Optional[str]): Name of sheet containing the chart. If None, uses active sheet.
        new_name (Optional[str]): New name to assign to the chart. If None, name remains unchanged.
        new_chart_type (Optional[ExcelChartType]): New chart type to set. If None, chart type remains unchanged.
        source_sheet_range (Optional[ExcelRange]): New Excel range for chart data (e.g., "A1:B10").
                                                   If None, source data remains unchanged.
        source_book_name (Optional[str]): Name of workbook containing new source data. If None, uses active workbook.
        source_sheet_name (Optional[str]): Name of sheet containing new source data. If None, uses active sheet.
        dest_sheet_range (Optional[ExcelRange]): New Excel range for chart position and size (e.g., "D1:E10").
                                                 If None, position remains unchanged.
        dest_book_name (Optional[str]): Name of workbook for destination. If None, uses active workbook.
        dest_sheet_name (Optional[str]): Name of sheet for destination. If None, uses active sheet.

    Returns:
        str: The name of the chart after modifications (either original name or new name if changed).

    Note:
        - At least one of new_name, source_sheet_range, dest_sheet_range,
          or new_chart_type must be provided to make any changes.
        - The chart must exist in the specified workbook/sheet.
        - If changing source data from a different workbook/sheet, both must be open.
        - The source data should be properly formatted for the chart type.
        - The dest_sheet_range determines the new position and size of the chart if provided.
        - When moving a chart to a different sheet, both source and destination sheets must be open.
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

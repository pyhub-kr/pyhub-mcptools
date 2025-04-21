from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.forms import PivotTableCreateForm
from pyhub.mcptools.excel.types import (
    ExcelAggregationType,
    ExcelExpandMode,
)
from pyhub.mcptools.excel.utils import get_range, get_sheet, json_dumps, str_to_list
from pyhub.mcptools.excel.utils.tables import PivotTable


# TODO: macOS에서 xlwings 활용 테이블 생성 시에 오류 발생
@mcp.tool(enabled=OS.current_is_windows(), run_in_process=True, timeout=5)
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
        description=(
            "Possible strings: 'TableStyleLightN' (where N is 1-21), "
            "'TableStyleMediumN' (where N is 1-28), 'TableStyleDarkN' (where N is 1-11)"
        ),
        examples=["TableStyleMedium2"],
    ),
) -> str:
    """
    Convert Excel range to table.
    """

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

    sheet = source_range_.sheet

    # TODO: 윈도우에서는 동작하지만, macOS에서는 오류 발생.
    # https://docs.xlwings.org/en/stable/api/tables.html
    table = sheet.tables.add(
        source=source_range_.expand("table"),
        name=table_name or None,
        has_headers=has_headers,
        table_style_name=table_style_name,
    )

    # TODO: 이미 테이블일 때, 다시 테이블 변환은 안 됩니다. 아래 코드로 테이블을 해제시킬 수 있을 듯 한데, 멈춰있습니다.
    # current_sheet.api.ListObjects(table_name).UnList()  # Or, table.api.UnList()

    return f"Table(name='{table.name}') created successfully."


# TODO: table 목록/내역 반환


@mcp.tool(run_in_process=True, timeout=5)
@macos_excel_request_permission
def excel_add_pivot_table(
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
    expand_mode: str = Field(
        default=ExcelExpandMode.get_none_value(),
        description=ExcelExpandMode.get_description("Mode for automatically expanding the selection range"),
    ),
    row_field_names: str = Field(
        description="Comma-separated field names to use as row fields. Must be column names from the source data.",
        examples=["Product", "Region", "Category,Subcategory"],
    ),
    column_field_names: str = Field(
        default="",
        description="Comma-separated field names to use as column fields. Must be column names from the source data.",
        examples=["Year", "Month", "Quarter,Month"],
    ),
    page_field_names: str = Field(
        default="",
        description=(
            "Comma-separated field names to use as page/filter fields. Must be column names from the source data."
        ),
        examples=["Country", "Department", "Region,Country"],
    ),
    value_fields: str = Field(
        description=(
            "Value fields in 'field_name:agg_func' format separated by '|'. \n"
            f"Supported agg func: {', '.join(ExcelAggregationType.names)}"
        ),
        examples=[
            f"Revenue:{ExcelAggregationType.SUM.name}",
            f"Units:{ExcelAggregationType.COUNT.name}|"
            f"Price:{ExcelAggregationType.AVERAGE.name}|Profit:{ExcelAggregationType.MAX.name}",
        ],
    ),
    pivot_table_name: str = Field(
        default="",
        description="Name for the pivot table. Must be specified and unique within the sheet.",
        examples=["SalesPivot", "RegionalAnalysis", "ProductSummary"],
    ),
) -> str:
    """
    Create a pivot table from Excel range data.

    Creates a pivot table at the destination range using data from the source range.
    Supports row, column, and page fields with customizable data aggregation.

    Important Usage Guide:
    Before creating a pivot table, it's essential to:
    1. Analyze the source data structure with the user
    2. Discuss and recommend appropriate column selections:
       - Row fields: Suggest categorical columns that make sense as row headers
       - Column fields: Recommend time-based or categorical columns for column headers
       - Page/Filter fields: Identify high-level grouping columns for filtering
       - Value fields: Determine which numeric columns to aggregate and how
    3. Get user confirmation on the selected fields and aggregation methods
    4. Proceed with pivot table creation only after user approval

    Note:
    - Pivot table name must be specified and unique within the sheet
    - Source data must have column headers
    - Value fields support multiple aggregation types (sum, count, average, max, min)
    - You only need to specify the data range, not necessarily a table - any valid Excel range with headers can be used
    - When examining column structure, only the first 5 rows of data are read to improve performance

    Example Discussion Flow:
    1. "Let's examine your data columns first."
    2. "Based on your data, I recommend:
       - Using 'Product' and 'Category' as row fields for hierarchical grouping
       - 'Month' as a column field for time-based analysis
       - 'Region' as a page field for filtering
       - 'Sales' and 'Quantity' as data fields with sum and average aggregations"
    3. "Would you like to proceed with these selections or adjust them?"

    Returns:
        str: Success or error message
    """

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

    form = PivotTableCreateForm(
        source_range=source_range,
        dest_range=dest_range,
        data={
            "row_field_names": row_field_names,
            "column_field_names": column_field_names,
            "page_field_names": page_field_names,
            "value_fields": value_fields,
            "pivot_table_name": pivot_table_name,
        },
    )
    form.is_valid(raise_exception=True)
    created_pivot_table_name = form.save()

    #
    # 피봇 테이블 생성
    #

    return f"Pivot table(name={created_pivot_table_name}) created successfully."


@mcp.tool(run_in_process=True, timeout=5)
@macos_excel_request_permission
def excel_get_pivot_tables(
    book_name: str = Field(default=""),
    sheet_name: str = Field(default=""),
) -> str:
    """
    Get information about all pivot tables in an Excel worksheet.

    Returns a JSON string containing details of all pivot tables in the specified worksheet.

    Note:
    - If no book or sheet is specified, the active workbook and sheet will be used
    """

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
    return json_dumps(PivotTable.list(sheet))


@mcp.tool(run_in_process=True, timeout=5)
@macos_excel_request_permission
def excel_remove_pivot_tables(
    remove_all: bool = Field(default=False, description="Remove all pivot tables."),
    pivot_table_names: str = Field(default="", description="Comma-separated pivot table names"),
    book_name: str = Field(default=""),
    sheet_name: str = Field(default=""),
) -> str:
    """
    Remove pivot tables from an Excel worksheet.

    Use remove_all=True to delete all pivot tables in a specific sheet,
    or provide pivot_table_names to remove individual pivot tables.

    Note:
    - Modifying existing pivot table designs is not supported
    - To change a pivot table's configuration, remove it and create a new one
    """

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    if remove_all:
        return PivotTable.remove_all(sheet)

    else:
        return PivotTable.remove(sheet, str_to_list(pivot_table_names))

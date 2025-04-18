from django.core.exceptions import ValidationError
from pydantic import Field
from xlwings.constants import PivotFieldOrientation, PivotTableSourceType

from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.types import (
    ExcelAggregationType,
    ExcelExpandMode,
)
from pyhub.mcptools.excel.utils import get_range, get_sheet, json_dumps, str_to_list
from pyhub.mcptools.excel.utils.tables import get_pivot_tables


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
        description=(
            "Possible strings: 'TableStyleLightN' (where N is 1-21), "
            "'TableStyleMediumN' (where N is 1-28), 'TableStyleDarkN' (where N is 1-11)"
        ),
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

    sheet = source_range_.sheet

    # https://docs.xlwings.org/en/stable/api/tables.html
    table = sheet.tables.add(
        source=source_range_.expand("table"),
        name=table_name or None,
        has_headers=has_headers,
        table_style_name=table_style_name,
    )

    # TODO: 이미 테이블일 때, 다시 테이블 변환은 안 됩니다. 아래 코드로 테이블을 해제시킬 수 있음.
    # current_sheet.api.ListObjects(table_name).UnList()

    return f"Table(name='{table.name}') created successfully."


@mcp.tool()
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
        default="",
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
        default="",
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
    pivot_table_name: str = Field(default=""),
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
    - Windows only feature
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
        str: Success message or error message
    """

    # macOS 엑셀에서는 지원하지 않습니다.
    if OS.current_is_windows() is False:
        return "Error: This feature is only supported on Windows."

    source_range_ = get_range(
        sheet_range=source_sheet_range,
        book_name=source_book_name,
        sheet_name=source_sheet_name,
        expand_mode=expand_mode,
    )
    dest_range_ = get_range(
        sheet_range=dest_sheet_range,
        book_name=dest_book_name,
        sheet_name=dest_sheet_name,
    )

    sheet = source_range_.sheet

    #
    # 인자 전처리 및 검증
    #

    # 소스 데이터의 컬럼명 집합 추출
    column_names_set = set(source_range_[0].expand("right").value)

    # 인자로 지정된 데이터의 컬럼명 추출

    row_field_names_list = str_to_list(row_field_names, ",")
    column_field_names_list = str_to_list(column_field_names, ",")
    page_field_names_list = str_to_list(page_field_names, ",")

    # 필드명 유효성 검사
    for field_list, field_type in [
        (row_field_names_list, "Row fields"),
        (column_field_names_list, "Column fields"),
        (page_field_names_list, "Page fields"),
    ]:
        invalid_fields = set(field_list) - column_names_set
        if invalid_fields and field_list != {""}:  # 빈 문자열이 아닌 경우에만 검사
            raise ValidationError(f"{field_type} contain invalid field names: {', '.join(invalid_fields)}")

    value_fields_set = str_to_list(value_fields, "|")
    data_item_list = []
    # 값 필드 설정 (문자열 파싱)
    if value_fields_set:
        for item in value_fields_set:
            parts = item.split(":")

            field_name = parts[0]
            if field_name not in column_names_set:
                raise ValidationError(f"value_fields contain invalid field name: {field_name}")

            agg_func_name = parts[1] if len(parts) > 1 else "SUM"
            agg_func = getattr(ExcelAggregationType, agg_func_name.upper())

            data_item_list.append(
                {
                    "field_name": field_name,
                    "agg_func": agg_func,
                }
            )

    #
    # 피봇 테이블 생성
    #

    # 캐시 생성 (xlDatabase: 워크시트 범위 기반)
    pivot_cache = sheet.api.Parent.PivotCaches().Create(
        SourceType=PivotTableSourceType.xlDatabase,  # 워크시트 기반 캐시
        SourceData=source_range_.api,
    )

    pivot_table = pivot_cache.CreatePivotTable(
        TableDestination=dest_range_.api,
        TableName=pivot_table_name or None,
    )

    # TODO: 노출이 불필요한 필드는 숨길 수 있어요. PivotFieldOrientation.xlHidden

    if row_field_names_list:
        for name in row_field_names_list:
            pivot_field = pivot_table.PivotFields(name)
            pivot_field.Orientation = PivotFieldOrientation.xlRowField

    if column_field_names_list:
        for position, name in enumerate(column_field_names_list, 1):
            pivot_field = pivot_table.PivotFields(name)
            pivot_field.Orientation = PivotFieldOrientation.xlColumnField
            pivot_field.Position = position

    if page_field_names_list:
        for name in page_field_names_list:
            pivot_field = pivot_table.PivotFields(name)
            pivot_field.Orientation = PivotFieldOrientation.xlPageField

    # 값 필드 설정 (문자열 파싱)
    if data_item_list:
        for item in data_item_list:
            data_field = pivot_table.AddDataField(
                pivot_table.PivotFields(item["field_name"]),
            )
            data_field.Function = item["agg_func"]
            # data_field.NumberFormat = "#,##0"  # 천 단위 구분 기호

    pivot_table.RefreshTable()

    return "Pivot table created successfully."


@mcp.tool()
@macos_excel_request_permission
def excel_get_pivot_tables(
    book_name: str = Field(default=""),
    sheet_name: str = Field(default=""),
) -> str:
    """
    Get information about all pivot tables in an Excel worksheet.

    Returns a JSON string containing details of all pivot tables in the specified worksheet.

    Note:
    - This feature is only supported on Windows
    - If no book or sheet is specified, the active workbook and sheet will be used
    """
    if OS.current_is_windows() is False:
        return "Error: This feature is only supported on Windows."

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
    return json_dumps(get_pivot_tables(sheet))


@mcp.tool()
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
    - This feature is only supported on Windows
    - Modifying existing pivot table designs is not supported
    - To change a pivot table's configuration, remove it and create a new one
    """
    # macOS 엑셀에서는 지원하지 않습니다.
    if OS.current_is_windows() is False:
        return "Error: This feature is only supported on Windows."

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    names = []
    if remove_all:
        pivot_table_api = sheet.api.PivotTables()
        for i in range(1, pivot_table_api.Count + 1):
            pivot_table = pivot_table_api.Item(i)
            names.append(pivot_table.Name)
            pivot_table.TableRange2.Delete()
            try:
                pivot_table.PivotCache().Delete()
            except:  # noqa
                pass
    else:
        for name in str_to_list(pivot_table_names):
            pivot_table = sheet.api.PivotTables(name)
            names.append(pivot_table.Name)
            pivot_table.TableRange2.Delete()
            try:
                pivot_table.PivotCache().Delete()
            except:  # noqa
                pass

    if names:
        return f"Removed pivot tables : {', '.join(names)}"
    else:
        return "No pivot tables were removed."

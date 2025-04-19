from typing import Optional

import xlwings as xw
from xlwings.constants import PivotFieldOrientation, PivotTableSourceType

from pyhub.mcptools.core.choices import OS


def create_pivot_table(
    source_range: xw.Range,
    dest_range: xw.Range,
    row_field_names_list: list[str],
    column_field_names_list: list[str],
    page_field_names_list: list[str],
    value_fields: list[dict],
    pivot_table_name: Optional[str] = None,
) -> None:
    sheet = source_range.sheet

    if OS.current_is_windows():
        # 캐시 생성 (xlDatabase: 워크시트 범위 기반)
        pivot_cache = sheet.api.Parent.PivotCaches().Create(
            SourceType=PivotTableSourceType.xlDatabase,  # 워크시트 기반 캐시
            SourceData=source_range.api,
        )

        pivot_table = pivot_cache.CreatePivotTable(
            TableDestination=dest_range.api,
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
        if value_fields:
            for item in value_fields:
                data_field = pivot_table.AddDataField(
                    pivot_table.PivotFields(item["field_name"]),
                )
                data_field.Function = item["agg_func"]
                # data_field.NumberFormat = "#,##0"  # 천 단위 구분 기호

        pivot_table.RefreshTable()

    else:
        raise NotImplementedError(f"Unsupported OS: {OS.get_current()}")


def get_pivot_tables(sheet: xw.Sheet) -> list:
    if OS.current_is_windows() is False:
        return []

    pivot_table_api = sheet.api.PivotTables()

    count = pivot_table_api.Count

    pivot_tables = []
    for idx in range(1, count + 1):
        pivot_table = pivot_table_api.Item(idx)
        all_fields = pivot_table.PivotFields()

        name = pivot_table.Name  # 피벗 테이블 이름
        source_addr = pivot_table.PivotCache().SourceData  # 원본 데이터 범위
        try:
            dest_addr = pivot_table.Location
        except:  # noqa
            dest_addr = pivot_table.TableRange2.Address

        row_field_names = []
        column_field_names = []
        page_field_names = []
        value_field_names = []

        for i in range(1, all_fields.Count + 1):
            fld = all_fields.Item(i)
            ori = fld.Orientation
            name = fld.Name

            match ori:
                case PivotFieldOrientation.xlRowField:
                    row_field_names.append(name)
                case PivotFieldOrientation.xlColumnField:
                    column_field_names.append(name)
                case PivotFieldOrientation.xlPageField:
                    page_field_names.append(name)
                case PivotFieldOrientation.xlDataField:
                    value_field_names.append(name)

        pivot_tables.append(
            {
                "name": name,
                "source_addr": source_addr,
                "dest_addr": dest_addr,
                "row_field_names": row_field_names,
                "column_field_names": column_field_names,
                "page_field_names": page_field_names,
                "value_field_names": value_field_names,
            }
        )

    return pivot_tables

import xlwings as xw
from xlwings.constants import PivotFieldOrientation

from pyhub.mcptools.core.choices import OS


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

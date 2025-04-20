import platform
from typing import Optional

import xlwings as xw
from xlwings.constants import PivotFieldOrientation, PivotTableSourceType

from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.utils import applescript_run_sync


class UnsupportedOSError(Exception):
    """Exception raised when PivotTable is not supported on current OS"""

    def __init__(self, os_name: str):
        self.message = f"PivotTable is not supported on {os_name}. Only Windows and macOS are supported."
        super().__init__(self.message)


class PivotTable:
    def __init__(
        self,
        source_range: xw.Range,
        dest_range: xw.Range,
        row_field_names_list: list[str],
        column_field_names_list: list[str],
        page_field_names_list: list[str],
        value_fields: list[dict],
        pivot_table_name: Optional[str] = None,
    ):
        self.source_range = source_range
        self.dest_range = dest_range
        self.row_field_names_list = row_field_names_list
        self.column_field_names_list = column_field_names_list
        self.page_field_names_list = page_field_names_list
        self.value_fields = value_fields
        self.pivot_table_name = pivot_table_name

    @classmethod
    def create(cls, **kwargs) -> None:
        """Create appropriate PivotTable instance for the current OS

        Returns:
            PivotTable: OS-specific PivotTable instance

        Raises:
            UnsupportedOSError: If current OS is neither Windows nor macOS
        """

        match OS.get_current():
            case OS.WINDOWS:
                return PivotTableInWindows(**kwargs).create_()
            case OS.MACOS:
                return PivotTableInMacOS(**kwargs).create_()
            case _:
                raise UnsupportedOSError(platform.system())

    def create_(self):
        raise NotImplementedError


class PivotTableInWindows(PivotTable):
    def create_(self):
        sheet = self.source_range.sheet

        pivot_cache = sheet.api.Parent.PivotCaches().Create(
            SourceType=PivotTableSourceType.xlDatabase,  # 워크시트 기반 캐시
            SourceData=self.source_range.api,
        )

        pivot_table = pivot_cache.CreatePivotTable(
            TableDestination=self.dest_range.api,
            TableName=self.pivot_table_name or None,
        )

        # TODO: 노출이 불필요한 필드는 숨길 수 있어요. PivotFieldOrientation.xlHidden

        if self.row_field_names_list:
            for name in self.row_field_names_list:
                pivot_field = pivot_table.PivotFields(name)
                pivot_field.Orientation = PivotFieldOrientation.xlRowField

        if self.column_field_names_list:
            for name in self.column_field_names_list:
                pivot_field = pivot_table.PivotFields(name)
                pivot_field.Orientation = PivotFieldOrientation.xlColumnField
                # pivot_field.Position = position

        if self.page_field_names_list:
            for name in self.page_field_names_list:
                pivot_field = pivot_table.PivotFields(name)
                pivot_field.Orientation = PivotFieldOrientation.xlPageField

        # 값 필드 설정 (문자열 파싱)
        if self.value_fields:
            for item in self.value_fields:
                data_field = pivot_table.AddDataField(
                    pivot_table.PivotFields(item["field_name"]),
                )
                data_field.Function = item["agg_func"]
                # data_field.NumberFormat = "#,##0"  # 천 단위 구분 기호

        pivot_table.RefreshTable()


class PivotTableInMacOS(PivotTable):
    template_path = "excel/pivot_table_create.applescript"

    def create_(self):
        sheet = self.source_range.sheet
        workbook = sheet.book

        applescript_run_sync(
            template_path=self.template_path,
            context={
                "workbook_name": workbook.name,
                "sheet_name": sheet.name,
                "source_range_address": self.source_range.address,
                "dest_range_address": self.dest_range.address,
                "pivot_table_name": self.pivot_table_name or "PivotTable1",
                "row_field_names_list": self.row_field_names_list,
                "column_field_names_list": self.column_field_names_list,
                "page_field_names_list": self.page_field_names_list,
                "value_fields": self.value_fields,
            },
        )


def create_pivot_table(
    source_range: xw.Range,
    dest_range: xw.Range,
    row_field_names_list: list[str],
    column_field_names_list: list[str],
    page_field_names_list: list[str],
    value_fields: list[dict],
    pivot_table_name: Optional[str] = None,
) -> None:

    return PivotTable.create(
        source_range=source_range,
        dest_range=dest_range,
        row_field_names_list=row_field_names_list,
        column_field_names_list=column_field_names_list,
        page_field_names_list=page_field_names_list,
        value_fields=value_fields,
        pivot_table_name=pivot_table_name,
    )


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

import csv
import platform
from io import StringIO
from typing import List, Optional

import xlwings as xw
from xlwings.constants import PivotFieldOrientation, PivotTableSourceType

from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.microsoft.excel.utils import applescript_run_sync


class UnsupportedOSError(Exception):
    """Exception raised when PivotTable is not supported on current OS"""

    def __init__(self, os_name: str):
        self.message = f"PivotTable is not supported on {os_name}. Only Windows and macOS are supported."
        super().__init__(self.message)


class PivotTable:
    @classmethod
    def create(
        cls,
        source_range: xw.Range,
        dest_range: xw.Range,
        row_field_names_list: List[str],
        column_field_names_list: List[str],
        page_field_names_list: List[str],
        value_fields: List[dict],
        pivot_table_name: Optional[str] = None,
    ) -> str:
        """Create appropriate PivotTable instance for the current OS

        Returns:
            str: Created PivotTable Name

        Raises:
            UnsupportedOSError: If current OS is neither Windows nor macOS
        """

        match OS.get_current():
            case OS.WINDOWS:
                return PivotTableInWindows.create_(
                    source_range=source_range,
                    dest_range=dest_range,
                    row_field_names_list=row_field_names_list,
                    column_field_names_list=column_field_names_list,
                    page_field_names_list=page_field_names_list,
                    value_fields=value_fields,
                    pivot_table_name=pivot_table_name,
                )
            case OS.MACOS:
                return PivotTableInMacOS.create_(
                    source_range=source_range,
                    dest_range=dest_range,
                    row_field_names_list=row_field_names_list,
                    column_field_names_list=column_field_names_list,
                    page_field_names_list=page_field_names_list,
                    value_fields=value_fields,
                    pivot_table_name=pivot_table_name,
                )
            case _:
                raise UnsupportedOSError(platform.system())

    @classmethod
    def list(cls, sheet: xw.Sheet) -> List:
        """시트 내 피봇 테이블 목록/내역을 반환합니다.

        Args:
            sheet (xw.Sheet): 피봇 테이블을 조회할 시트

        Returns:
            List: 피봇 테이블 목록

        Raises:
            UnsupportedOSError: 현재 OS가 Windows나 macOS가 아닌 경우
        """
        match OS.get_current():
            case OS.WINDOWS:
                return PivotTableInWindows.list_(sheet=sheet)
            case OS.MACOS:
                return PivotTableInMacOS.list_(sheet=sheet)
            case _:
                raise UnsupportedOSError(platform.system())

    @classmethod
    def remove(cls, sheet: xw.Sheet, names: List[str]) -> str:
        """지정된 이름의 피봇 테이블을 삭제하고 삭제된 피봇 테이블 이름 목록을 반환합니다.

        Args:
            sheet (xw.Sheet): 피봇 테이블이 있는 시트
            names (List[str]): 삭제할 피봇 테이블 이름 목록

        Returns:
            List[str]: 삭제된 피봇 테이블 이름 목록

        Raises:
            UnsupportedOSError: 현재 OS가 Windows나 macOS가 아닌 경우
        """
        match OS.get_current():
            case OS.WINDOWS:
                return PivotTableInWindows.remove_(sheet=sheet, names=names)
            case OS.MACOS:
                return PivotTableInMacOS.remove_(sheet=sheet, names=names)
            case _:
                raise UnsupportedOSError(platform.system())

    @classmethod
    def remove_all(cls, sheet: xw.Sheet) -> str:
        """지정된 시트의 모든 피봇 테이블을 삭제하고 삭제된 피봇 테이블 이름 목록을 반환합니다.

        Args:
            sheet (xw.Sheet): 피봇 테이블을 모두 삭제할 시트

        Returns:
            List[str]: 삭제된 피봇 테이블 이름 목록

        Raises:
            UnsupportedOSError: 현재 OS가 Windows나 macOS가 아닌 경우
        """
        match OS.get_current():
            case OS.WINDOWS:
                return PivotTableInWindows.remove_all_(sheet=sheet)
            case OS.MACOS:
                return PivotTableInMacOS.remove_all_(sheet=sheet)
            case _:
                raise UnsupportedOSError(platform.system())


class PivotTableInWindows(PivotTable):
    @classmethod
    def create_(
        cls,
        source_range: xw.Range,
        dest_range: xw.Range,
        row_field_names_list: List[str],
        column_field_names_list: List[str],
        page_field_names_list: List[str],
        value_fields: List[dict],
        pivot_table_name: Optional[str] = None,
    ) -> str:
        sheet = source_range.sheet

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
            for name in column_field_names_list:
                pivot_field = pivot_table.PivotFields(name)
                pivot_field.Orientation = PivotFieldOrientation.xlColumnField
                # pivot_field.Position = position

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

        return pivot_table.name

    @classmethod
    def list_(cls, sheet: xw.Sheet) -> List:
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

    @classmethod
    def remove_(cls, sheet: xw.Sheet, names: List[str]) -> str:
        for name in names:
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

    @classmethod
    def remove_all_(cls, sheet: xw.Sheet) -> str:
        names = []
        pivot_table_api = sheet.api.PivotTables()
        for i in range(1, pivot_table_api.Count + 1):
            pivot_table = pivot_table_api.Item(i)
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


class PivotTableInMacOS(PivotTable):
    create_template_path = "excel/pivot_table_create.applescript"
    list_template_path = "excel/pivot_table_list.applescript"
    remove_template_path = "excel/pivot_table_remove.applescript"

    # TODO: 다른 시트에 대해서도 생성 지원 (현재는 같은 시트만 지원됨)
    @classmethod
    def create_(
        cls,
        source_range: xw.Range,
        dest_range: xw.Range,
        row_field_names_list: List[str],
        column_field_names_list: List[str],
        page_field_names_list: List[str],
        value_fields: List[dict],
        pivot_table_name: Optional[str] = None,
    ) -> str:
        sheet = source_range.sheet
        workbook = sheet.book

        created_pivottable_name = applescript_run_sync(
            template_path=cls.create_template_path,
            context={
                "workbook_name": workbook.name,
                "sheet_name": sheet.name,
                "source_range_address": source_range.address,
                "dest_range_address": dest_range.address,
                "pivot_table_name": pivot_table_name,
                "row_field_names_list": row_field_names_list,
                "column_field_names_list": column_field_names_list,
                "page_field_names_list": page_field_names_list,
                "value_fields": value_fields,
            },
        )
        return created_pivottable_name

    @classmethod
    def list_(cls, sheet: xw.Sheet) -> List:
        workbook = sheet.book

        stdout = applescript_run_sync(
            template_path=cls.list_template_path,
            context={
                "workbook_name": workbook.name,
                "sheet_name": sheet.name,
            },
        ).strip()

        # applescript 내에서는 JSON 포맷 생성이 번거로우므로, 아래의 text를 파싱하여 리스트로 변환
        # name: PivotTable1
        # source_addr: Sheet1!R1C1:R249C8
        # dest_addr: Sheet1!$J$1:$O$18
        # row_field_names: ["지역", "매장", "데이터"]
        # column_field_names: ["제품카테고리"]
        # page_field_names: ["제품명"]
        # value_field_names: ["합계 : 총액", "합계 : 판매수량"]
        # ---
        pivot_tables = []

        for pivot_table_text in stdout.split("---"):
            pivot_table_text = pivot_table_text.strip()

            pivot_table_info = {}

            for line in pivot_table_text.splitlines():
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # 값이 [ 로 시작하고 ]로 끝나면 리스트로 파싱
                if value.startswith("[") and value.endswith("]"):
                    value = value[1:-1]  # 대괄호 제거
                    if value:
                        # CSV 형식의 문자열을 안전하게 파싱
                        reader = csv.reader(StringIO(value))
                        value = [item.strip().strip("\"'") for item in next(reader)]
                    else:
                        value = []

                pivot_table_info[key] = value

            if pivot_table_info:
                pivot_tables.append(pivot_table_info)

        return pivot_tables

    @classmethod
    def remove_(cls, sheet: xw.Sheet, names: List[str]) -> str:
        workbook = sheet.book

        # applescript 내에서 삭제 내역을 표준출력
        return applescript_run_sync(
            template_path=cls.remove_template_path,
            context={
                "workbook_name": workbook.name,
                "sheet_name": sheet.name,
                "remove_all": False,
                "names": names,
            },
        )

    @classmethod
    def remove_all_(cls, sheet: xw.Sheet) -> str:
        workbook = sheet.book

        # applescript 내에서 삭제 내역을 표준출력
        return applescript_run_sync(
            template_path=cls.remove_template_path,
            context={
                "workbook_name": workbook.name,
                "sheet_name": sheet.name,
                "remove_all": True,
            },
        )

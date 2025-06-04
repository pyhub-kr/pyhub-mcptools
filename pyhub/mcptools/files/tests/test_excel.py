"""Excel 파일 도구 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyhub.mcptools.files.tools.excel import (
    file__excel_convert,
    file__excel_format,
    file__excel_info,
    file__excel_merge,
    file__excel_read,
    file__excel_write,
    is_excel_file,
)


class TestExcelFileHelpers:
    """헬퍼 함수 테스트."""

    def test_is_excel_file(self):
        """Excel 파일 확장자 체크 테스트."""
        assert is_excel_file("test.xlsx") is True
        assert is_excel_file("test.xls") is True
        assert is_excel_file("test.xlsm") is True
        assert is_excel_file("test.xlsb") is True
        assert is_excel_file("test.XLSX") is True  # 대소문자
        assert is_excel_file("test.csv") is False
        assert is_excel_file("test.txt") is False


class TestExcelFileRead:
    """excel_file_read 도구 테스트."""

    @pytest.mark.asyncio
    async def test_read_excel_file_not_excel(self):
        """Excel 파일이 아닌 경우 에러."""
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            await file__excel_read(file_path="test.txt")

    @pytest.mark.asyncio
    async def test_read_excel_file_success(self):
        """Excel 파일 읽기 성공 테스트."""
        # Mock openpyxl
        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = b"excel_bytes"

            # openpyxl을 모킹하여 ImportError 방지
            mock_openpyxl = MagicMock()
            with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                # Mock 워크북과 워크시트
                mock_ws = type(
                    "MockWorksheet",
                    (),
                    {
                        "min_row": 1,
                        "max_row": 2,
                        "min_column": 1,
                        "max_column": 2,
                        "iter_rows": lambda self, **kwargs: [["A1", "B1"], ["A2", "B2"]],
                    },
                )()

                mock_wb = type(
                    "MockWorkbook",
                    (),
                    {"sheetnames": ["Sheet1"], "active": mock_ws, "__getitem__": lambda self, name: mock_ws},
                )()

                mock_openpyxl.load_workbook.return_value = mock_wb

                result = await file__excel_read(file_path="/test/file.xlsx", sheet_name="", range="")

                assert "A1,B1" in result
                assert "A2,B2" in result
                mock_read.assert_called_once_with("/test/file.xlsx")


class TestExcelFileWrite:
    """excel_file_write 도구 테스트."""

    @pytest.mark.asyncio
    async def test_write_excel_file_not_excel(self):
        """Excel 파일이 아닌 경우 에러."""
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            await file__excel_write(file_path="test.txt", data="a,b\n1,2")

    @pytest.mark.asyncio
    async def test_write_excel_file_success(self):
        """Excel 파일 쓰기 성공 테스트."""
        test_data = "Name,Age\nJohn,30\nJane,25"

        with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock) as mock_write:
            with patch(
                "pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock
            ) as mock_read:
                # 파일이 없다고 가정 (overwrite=False 테스트)
                mock_read.side_effect = ValueError("File not found")

                # openpyxl 모킹
                mock_openpyxl = MagicMock()
                with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                    mock_ws = type("MockWorksheet", (), {"title": None, "append": lambda self, row: None})()

                    mock_wb = type("MockWorkbook", (), {"active": mock_ws, "save": lambda self, buffer: None})()

                    mock_openpyxl.Workbook.return_value = mock_wb

                    result = await file__excel_write(file_path="/test/output.xlsx", data=test_data)

                    assert "저장되었습니다" in result
                    assert "/test/output.xlsx" in result
                    mock_write.assert_called_once()


class TestExcelFileInfo:
    """excel_file_info 도구 테스트."""

    @pytest.mark.asyncio
    async def test_info_excel_file_success(self):
        """Excel 파일 정보 조회 성공 테스트."""
        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = b"excel_bytes"

            # openpyxl 모킹
            mock_openpyxl = MagicMock()
            with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                mock_ws1 = type("MockWorksheet", (), {"max_row": 10, "max_column": 5})()

                mock_ws2 = type("MockWorksheet", (), {"max_row": 20, "max_column": 3})()

                mock_wb = type(
                    "MockWorkbook",
                    (),
                    {
                        "sheetnames": ["Sheet1", "Sheet2"],
                        "__getitem__": lambda self, name: mock_ws1 if name == "Sheet1" else mock_ws2,
                    },
                )()

                mock_openpyxl.load_workbook.return_value = mock_wb

                result = await file__excel_info(file_path="/test/file.xlsx")

                # JSON 파싱하여 확인
                import json

                info = json.loads(result)

                assert info["file_path"] == "/test/file.xlsx"
                assert info["sheet_count"] == 2
                assert len(info["sheets"]) == 2
                assert info["sheets"][0]["name"] == "Sheet1"
                assert info["sheets"][0]["rows"] == 10
                assert info["sheets"][0]["columns"] == 5


class TestExcelFileConvert:
    """excel_file_convert 도구 테스트."""

    @pytest.mark.asyncio
    async def test_convert_xlsx_to_xls(self):
        """xlsx → xls 변환 테스트."""
        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock) as mock_write:
                mock_read.return_value = b"excel_bytes"

                # Mock openpyxl과 xlwt
                mock_openpyxl = MagicMock()
                mock_xlwt = MagicMock()

                with patch.dict("sys.modules", {"openpyxl": mock_openpyxl, "xlwt": mock_xlwt, "xlrd": MagicMock()}):
                    # Mock 워크북
                    mock_ws = MagicMock()
                    mock_ws.max_row = 10
                    mock_ws.max_column = 5
                    mock_ws.iter_rows.return_value = [["A1", "B1"], ["A2", "B2"]]

                    mock_wb = MagicMock()
                    mock_wb.sheetnames = ["Sheet1"]
                    mock_wb.__getitem__.return_value = mock_ws

                    mock_openpyxl.load_workbook.return_value = mock_wb

                    # Mock xls workbook
                    mock_xls_sheet = MagicMock()
                    mock_xls_book = MagicMock()
                    mock_xls_book.add_sheet.return_value = mock_xls_sheet
                    mock_xlwt.Workbook.return_value = mock_xls_book

                    result = await file__excel_convert(
                        source_path="/test/file.xlsx", target_path="/test/file.xls", target_format=""
                    )

                    assert "변환되었습니다" in result
                    mock_write.assert_called_once()


class TestExcelFileMerge:
    """excel_file_merge 도구 테스트."""

    @pytest.mark.asyncio
    async def test_merge_sheets_mode(self):
        """sheets 모드 병합 테스트."""
        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock) as mock_write:
                # 두 파일 읽기를 시뮬레이션
                mock_read.side_effect = [b"excel_bytes1", b"excel_bytes2"]

                mock_openpyxl = MagicMock()

                with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                    # Mock 워크북들
                    mock_ws1 = MagicMock()
                    mock_ws1.iter_rows.return_value = [["A1", "B1"], ["A2", "B2"]]

                    mock_wb1 = MagicMock()
                    mock_wb1.sheetnames = ["Sheet1"]
                    mock_wb1.__getitem__.return_value = mock_ws1

                    mock_wb2 = MagicMock()
                    mock_wb2.sheetnames = ["Sheet1"]
                    mock_wb2.__getitem__.return_value = mock_ws1

                    # 새 워크북
                    mock_new_wb = MagicMock()
                    mock_new_wb.sheetnames = []
                    mock_new_ws = MagicMock()
                    mock_new_wb.create_sheet.return_value = mock_new_ws

                    mock_openpyxl.load_workbook.side_effect = [mock_wb1, mock_wb2]
                    mock_openpyxl.Workbook.return_value = mock_new_wb

                    result = await file__excel_merge(
                        file_paths="/test/file1.xlsx, /test/file2.xlsx",
                        target_path="/test/merged.xlsx",
                        merge_mode="sheets",
                        sheet_prefix="",
                    )

                    assert "병합 완료" in result
                    mock_write.assert_called_once()


class TestPhase3Features:
    """Phase 3 기능 테스트 (수식/서식 지원)."""

    @pytest.mark.asyncio
    async def test_read_with_formula_option(self):
        """data_only 파라미터 테스트."""
        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = b"excel_bytes"

            mock_openpyxl = MagicMock()
            with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                mock_ws = MagicMock()
                mock_ws.min_row = 1
                mock_ws.max_row = 2
                mock_ws.min_column = 1
                mock_ws.max_column = 2
                mock_ws.iter_rows.return_value = [["=SUM(A1:A10)", "B1"], ["A2", "B2"]]

                mock_wb = MagicMock()
                mock_wb.sheetnames = ["Sheet1"]
                mock_wb.active = mock_ws
                mock_wb.__getitem__.return_value = mock_ws

                mock_openpyxl.load_workbook.return_value = mock_wb

                # data_only=False로 수식 자체를 읽기
                await file__excel_read(file_path="/test/file.xlsx", sheet_name="", range="", data_only=False)

                # load_workbook이 data_only=False로 호출되었는지 확인
                mock_openpyxl.load_workbook.assert_called_once()
                call_args = mock_openpyxl.load_workbook.call_args
                assert call_args[1]["data_only"] is False

    @pytest.mark.asyncio
    async def test_write_with_header_format(self):
        """헤더 서식 적용 테스트."""
        test_data = "Name,Age,Salary\nJohn,30,50000\nJane,25,45000"

        with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock):
            with patch(
                "pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock
            ) as mock_read:
                mock_read.side_effect = ValueError("File not found")

                mock_openpyxl = MagicMock()
                mock_styles = MagicMock()

                with patch.dict("sys.modules", {"openpyxl": mock_openpyxl, "openpyxl.styles": mock_styles}):
                    # Mock 워크시트와 셀
                    mock_cells = {}

                    def create_cell(row, column):
                        key = (row, column)
                        if key not in mock_cells:
                            mock_cell = MagicMock()
                            mock_cell.column_letter = chr(ord("A") + column - 1)  # 1->A, 2->B, etc.
                            mock_cells[key] = mock_cell
                        return mock_cells[key]

                    mock_ws = MagicMock()
                    mock_ws.title = None
                    mock_ws.append = MagicMock()
                    mock_ws.cell.side_effect = create_cell

                    # column_dimensions를 MagicMock으로 설정
                    mock_column_dim = MagicMock()
                    mock_ws.column_dimensions = MagicMock()
                    mock_ws.column_dimensions.__getitem__.return_value = mock_column_dim

                    mock_wb = MagicMock()
                    mock_wb.active = mock_ws
                    mock_wb.save = MagicMock()

                    mock_openpyxl.Workbook.return_value = mock_wb

                    # Mock styles
                    mock_font = MagicMock()
                    mock_fill = MagicMock()
                    mock_alignment = MagicMock()

                    mock_styles.Font = MagicMock(return_value=mock_font)
                    mock_styles.PatternFill = MagicMock(return_value=mock_fill)
                    mock_styles.Alignment = MagicMock(return_value=mock_alignment)

                    result = await file__excel_write(file_path="/test/output.xlsx", data=test_data, header_format=True)

                    assert "저장되었습니다" in result
                    # 헤더 서식이 적용되었는지 확인
                    assert mock_ws.cell.called
                    # 첫 번째 행의 셀들이 서식이 적용되었는지 확인
                    first_cell = mock_cells.get((1, 1))
                    if first_cell:
                        assert first_cell.font == mock_font

    @pytest.mark.asyncio
    async def test_excel_file_format(self):
        """excel_file_format 도구 테스트."""
        format_options = {
            "header_row": True,
            "auto_filter": True,
            "freeze_panes": "A2",
            "column_widths": {"A": 20, "B": 15},
            "number_formats": {"C": "#,##0.00"},
        }

        with patch("pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock) as mock_read:
            with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock) as mock_write:
                mock_read.return_value = b"excel_bytes"

                mock_openpyxl = MagicMock()
                mock_styles = MagicMock()
                mock_utils = MagicMock()

                with patch.dict(
                    "sys.modules",
                    {"openpyxl": mock_openpyxl, "openpyxl.styles": mock_styles, "openpyxl.utils": mock_utils},
                ):
                    # Mock 워크시트
                    mock_cell = MagicMock()
                    mock_cell.value = "Header"

                    mock_ws = MagicMock()
                    mock_ws.dimensions = "A1:C10"
                    mock_ws.max_row = 10
                    mock_ws.__getitem__.return_value = [mock_cell]  # ws[1]
                    mock_ws.cell.return_value = mock_cell

                    # column_dimensions를 dict-like MagicMock으로 설정
                    mock_column_dim = MagicMock()
                    mock_ws.column_dimensions = MagicMock()
                    mock_ws.column_dimensions.__getitem__.return_value = mock_column_dim

                    mock_ws.auto_filter = MagicMock()

                    mock_wb = MagicMock()
                    mock_wb.sheetnames = ["Sheet1"]
                    mock_wb.active = mock_ws
                    mock_wb.__getitem__.return_value = mock_ws
                    mock_wb.save = MagicMock()

                    mock_openpyxl.load_workbook.return_value = mock_wb

                    # Mock styles
                    mock_styles.Font = MagicMock()
                    mock_styles.PatternFill = MagicMock()
                    mock_styles.Alignment = MagicMock()

                    # Mock utils
                    mock_utils.get_column_letter = MagicMock()

                    import json

                    result = await file__excel_format(
                        file_path="/test/file.xlsx",
                        sheet_name="",  # 명시적으로 빈 문자열 전달
                        format_options=json.dumps(format_options),
                        output_path="",  # 명시적으로 빈 문자열 전달
                    )

                    assert "서식이 적용되었습니다" in result

                    # 서식 적용 확인
                    assert mock_ws.freeze_panes == "A2"
                    assert mock_ws.auto_filter.ref == "A1:C10"
                    mock_write.assert_called_once()

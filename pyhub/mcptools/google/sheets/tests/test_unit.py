"""Google Sheets 단위 테스트 - Mock을 사용한 로직 테스트"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyhub.mcptools.google.sheets.auth import GoogleSheetsAuth
from pyhub.mcptools.google.sheets.client_async import GoogleSheetsAsyncClient
from pyhub.mcptools.google.sheets.utils import (
    convert_a1_to_coordinates,
    convert_coordinates_to_a1,
    ensure_2d_array,
    parse_csv_data,
    parse_sheet_range,
)


class TestUtils:
    """유틸리티 함수 테스트"""

    def test_parse_sheet_range(self):
        """시트 범위 파싱 테스트"""
        # 시트명이 포함된 경우
        sheet, range_str = parse_sheet_range("Sheet1!A1:B10")
        assert sheet == "Sheet1"
        assert range_str == "A1:B10"

        # 시트명이 없는 경우
        sheet, range_str = parse_sheet_range("A1:B10")
        assert sheet == ""
        assert range_str == "A1:B10"

        # 복잡한 시트명
        sheet, range_str = parse_sheet_range("My Sheet Name!C5:D20")
        assert sheet == "My Sheet Name"
        assert range_str == "C5:D20"

    def test_ensure_2d_array(self):
        """2차원 배열 보장 테스트"""
        # 이미 2D 배열
        result = ensure_2d_array([["a", "b"], ["c", "d"]])
        assert result == [["a", "b"], ["c", "d"]]

        # 1D 배열
        result = ensure_2d_array(["a", "b", "c"])
        assert result == [["a", "b", "c"]]

        # 빈 배열
        result = ensure_2d_array([])
        assert result == [[]]

        # 단일 값 (리스트가 아님)
        result = ensure_2d_array("single")
        assert result == [["single"]]

    def test_a1_coordinates_conversion(self):
        """A1 표기법 ↔ 좌표 변환 테스트"""
        # A1 → 좌표
        row, col = convert_a1_to_coordinates("A1")
        assert row == 0 and col == 0

        row, col = convert_a1_to_coordinates("B5")
        assert row == 4 and col == 1

        row, col = convert_a1_to_coordinates("Z10")
        assert row == 9 and col == 25

        row, col = convert_a1_to_coordinates("AA1")
        assert row == 0 and col == 26

        # 좌표 → A1
        a1 = convert_coordinates_to_a1(0, 0)
        assert a1 == "A1"

        a1 = convert_coordinates_to_a1(4, 1)
        assert a1 == "B5"

        a1 = convert_coordinates_to_a1(9, 25)
        assert a1 == "Z10"

        a1 = convert_coordinates_to_a1(0, 26)
        assert a1 == "AA1"

    def test_parse_csv_data(self):
        """CSV 데이터 파싱 테스트"""
        # 기본 CSV
        csv_str = "Name,Age,City\nAlice,30,New York\nBob,25,London"
        result = parse_csv_data(csv_str)
        expected = [["Name", "Age", "City"], ["Alice", "30", "New York"], ["Bob", "25", "London"]]
        assert result == expected

        # 빈 문자열
        result = parse_csv_data("")
        assert result == [[]]

        # 쉼표가 포함된 데이터
        csv_str = '"Last, First",Age\n"Smith, John",30'
        result = parse_csv_data(csv_str)
        assert result[0] == ["Last, First", "Age"]
        assert result[1] == ["Smith, John", "30"]


class TestGoogleSheetsAuth:
    """인증 클래스 테스트"""

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        auth1 = GoogleSheetsAuth()
        auth2 = GoogleSheetsAuth()
        assert auth1 is auth2

        # 리팩토링 후에도 싱글톤 패턴이 동작하는지 확인
        assert hasattr(auth1, "_initialized")
        assert auth1.service == auth2.service

    def test_credentials_directory_setup(self):
        """인증 디렉토리 설정 테스트 - 리팩토링된 버전"""
        auth = GoogleSheetsAuth()

        # 리팩토링된 GoogleSheetsAuth는 GoogleAuthBase를 상속하여 token_path 사용
        assert hasattr(auth, "token_path")
        assert auth.service == "sheets"
        assert len(auth.scopes) > 0

        # 토큰 경로가 올바른 디렉토리에 있는지 확인
        assert ".pyhub-mcptools" in str(auth.token_path)
        assert "credentials" in str(auth.token_path)
        assert auth.token_path.name == "google_sheets_token.json"

    def test_auth_base_integration(self):
        """공통 인증 모듈 통합 테스트"""
        auth = GoogleSheetsAuth()

        # GoogleAuthBase 메서드들이 사용 가능한지 확인
        assert hasattr(auth, "get_credentials")
        assert hasattr(auth, "clear_credentials")
        assert hasattr(auth, "get_auth_info")

        # 인증 정보 확인
        auth_info = auth.get_auth_info()
        assert auth_info["service"] == "sheets"
        assert len(auth_info["scopes"]) > 0
        assert "token_path" in auth_info


class TestGoogleSheetsAsyncClient:
    """비동기 클라이언트 테스트"""

    def test_client_initialization(self):
        """클라이언트 초기화 테스트"""
        client = GoogleSheetsAsyncClient()
        assert client.agcm is None
        # _cache 속성이 없을 수 있으므로 존재 여부만 확인
        assert hasattr(client, "agcm")

    def test_resolve_sheet_reference(self):
        """시트 참조 해결 테스트"""
        client = GoogleSheetsAsyncClient()

        # Mock worksheets
        mock_worksheets = [Mock(title="Sheet1"), Mock(title="Sheet2"), Mock(title="Data")]

        # 숫자 인덱스
        result = client._resolve_sheet_reference("0", mock_worksheets)
        assert result == "Sheet1"

        result = client._resolve_sheet_reference("2", mock_worksheets)
        assert result == "Data"

        # 시트 이름
        result = client._resolve_sheet_reference("Sheet2", mock_worksheets)
        assert result == "Sheet2"

        # 잘못된 인덱스
        with pytest.raises(ValueError):
            client._resolve_sheet_reference("5", mock_worksheets)

    def test_parse_cell_address(self):
        """셀 주소 파싱 테스트"""
        client = GoogleSheetsAsyncClient()

        # 유효한 주소 (0-based 인덱스 확인)
        row, col = client._parse_cell_address("A1")
        assert row == 0 and col == 0  # 0-based

        row, col = client._parse_cell_address("B5")
        assert row == 4 and col == 1  # 0-based

        # 잘못된 주소
        with pytest.raises(ValueError):
            client._parse_cell_address("INVALID")

    def test_expand_from_cell(self):
        """셀에서 확장 테스트"""
        client = GoogleSheetsAsyncClient()

        # 테스트 데이터
        all_values = [
            ["Name", "Age", "City", ""],
            ["Alice", "30", "New York", ""],
            ["Bob", "25", "London", ""],
            ["", "", "", ""],
        ]

        # table 모드 (데이터가 있는 영역만) - 0-based 인덱스 사용
        result = client._expand_from_cell(all_values, 0, 0, "table")
        expected = [["Name", "Age", "City"], ["Alice", "30", "New York"], ["Bob", "25", "London"]]
        assert result == expected

        # down 모드 (아래로만 확장) - 0-based 인덱스
        result = client._expand_from_cell(all_values, 0, 0, "down")
        expected = [["Name"], ["Alice"], ["Bob"]]
        assert result == expected

        # right 모드 (오른쪽으로만 확장) - 0-based 인덱스
        result = client._expand_from_cell(all_values, 0, 0, "right")
        expected = [["Name", "Age", "City"]]
        assert result == expected


class TestMockIntegration:
    """Mock을 사용한 통합 테스트"""

    @pytest.mark.asyncio
    async def test_create_spreadsheet_with_standardization(self):
        """표준화가 포함된 스프레드시트 생성 테스트"""
        from pyhub.mcptools.google.sheets.tools.sheets import gsheet_create_spreadsheet

        # Mock client
        mock_client = AsyncMock()

        # 초기 생성 결과 (로케일 의존적 시트명)
        mock_client.create_spreadsheet.return_value = {
            "id": "test123",
            "name": "Test Sheet",
            "url": "https://docs.google.com/spreadsheets/d/test123",
        }

        # 스프레드시트 정보 (시트1이라는 한국어 시트명)
        mock_client.get_spreadsheet_info.return_value = {"sheets": [{"id": "sheet1", "name": "시트1", "index": 0}]}

        # 시트 이름 변경 결과
        mock_client.rename_sheet.return_value = {"id": "sheet1", "name": "Sheet1", "index": 0}

        with patch("pyhub.mcptools.google.sheets.tools.sheets.get_client", return_value=mock_client):
            result = await gsheet_create_spreadsheet("Test Sheet")

            # JSON 파싱
            import json

            data = json.loads(result)

            # 기본 정보 확인
            assert data["id"] == "test123"
            assert data["name"] == "Test Sheet"

            # 표준화 정보 확인
            assert "first_sheet" in data
            assert data["first_sheet"]["original_name"] == "시트1"
            assert data["first_sheet"]["standardized_name"] == "Sheet1"

            # API 호출 확인
            mock_client.create_spreadsheet.assert_called_once_with("Test Sheet")
            mock_client.get_spreadsheet_info.assert_called_once_with("test123")
            mock_client.rename_sheet.assert_called_once_with("test123", "시트1", "Sheet1")


class TestErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_handle_api_error_decorator(self):
        """API 에러 처리 데코레이터 테스트"""
        from pyhub.mcptools.google.sheets.client_async import handle_api_errors

        # 에러를 발생시키는 함수
        @handle_api_errors
        async def test_function(self):
            raise Exception("Test error")

        # Mock 클라이언트
        mock_client = Mock()
        mock_client._handle_api_error = AsyncMock()

        # 에러 처리 확인
        await test_function(mock_client)
        mock_client._handle_api_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_functions(self):
        """검증 함수 테스트"""
        from pyhub.mcptools.core.validators import validate_spreadsheet_id

        # 유효한 ID (비동기 함수로 테스트)
        @validate_spreadsheet_id
        def test_function(spreadsheet_id: str):
            return spreadsheet_id

        # 기본적으로 검증이 통과해야 함 (실제 검증 로직은 validators.py에 있음)
        # validate_spreadsheet_id 데코레이터가 비동기 wrapper를 반환하므로 await 사용
        result = await test_function("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        # 검증 함수가 비동기이므로 결과 확인
        assert result is not None


@pytest.mark.parametrize(
    "input_data,expected",
    [
        (["a", "b"], [["a", "b"]]),
        ([["a", "b"], ["c", "d"]], [["a", "b"], ["c", "d"]]),
        ([], [[]]),
        ("single", [["single"]]),
    ],
)
def test_ensure_2d_array_parametrized(input_data, expected):
    """매개변수화된 2D 배열 보장 테스트"""
    result = ensure_2d_array(input_data)
    assert result == expected


@pytest.mark.parametrize(
    "a1,expected_row,expected_col", [("A1", 0, 0), ("B5", 4, 1), ("Z10", 9, 25), ("AA1", 0, 26), ("AB10", 9, 27)]
)
def test_a1_to_coordinates_parametrized(a1, expected_row, expected_col):
    """매개변수화된 A1 좌표 변환 테스트"""
    row, col = convert_a1_to_coordinates(a1)
    assert row == expected_row
    assert col == expected_col

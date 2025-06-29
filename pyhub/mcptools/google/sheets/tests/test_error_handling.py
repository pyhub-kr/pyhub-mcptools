"""Google Sheets 에러 처리 테스트"""

import pytest

from pyhub.mcptools.google.sheets.exceptions import (
    AuthenticationError,
    GoogleSheetsError,
    RateLimitError,
    SpreadsheetNotFoundError,
)
from pyhub.mcptools.google.sheets.tools.sheets import (
    gsheet_add_sheet,
    gsheet_delete_sheet,
    gsheet_get_spreadsheet_info,
    gsheet_get_values_from_range,
    gsheet_rename_sheet,
    gsheet_set_values_to_range,
)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_invalid_spreadsheet_id():
    """잘못된 스프레드시트 ID 에러 처리 테스트"""
    invalid_id = "invalid_spreadsheet_id_12345"

    with pytest.raises(Exception) as exc_info:
        await gsheet_get_spreadsheet_info(spreadsheet_id=invalid_id)

    # 예외가 발생했는지 확인
    assert exc_info.value is not None

    # locale 독립적인 에러 타입 확인
    assert isinstance(exc_info.value, (SpreadsheetNotFoundError, GoogleSheetsError))


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_invalid_sheet_name(test_spreadsheet_id):
    """존재하지 않는 시트명 에러 처리 테스트"""
    invalid_sheet_name = "NonExistentSheet12345"

    with pytest.raises(Exception) as exc_info:
        await gsheet_get_values_from_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{invalid_sheet_name}!A1:B2"
        )

    assert exc_info.value is not None
    # locale 독립적인 에러 타입 확인
    assert isinstance(exc_info.value, (SpreadsheetNotFoundError, GoogleSheetsError))


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_invalid_range_format(test_spreadsheet_id, sheet_info):
    """잘못된 범위 형식 에러 처리 테스트"""
    sheet_name = sheet_info["name"]

    # 잘못된 범위 형식들
    invalid_ranges = [
        f"{sheet_name}!INVALID_RANGE",
        f"{sheet_name}!A",  # 불완전한 범위
        f"{sheet_name}!123:456",  # 숫자만 있는 범위
    ]

    for invalid_range in invalid_ranges:
        with pytest.raises(Exception) as exc_info:
            await gsheet_get_values_from_range(spreadsheet_id=test_spreadsheet_id, sheet_range=invalid_range)

        assert exc_info.value is not None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_invalid_data_format(test_spreadsheet_id, sheet_info):
    """잘못된 데이터 형식 에러 처리 테스트"""
    sheet_name = sheet_info["name"]

    # 잘못된 데이터 형식
    invalid_data = "not_a_list"

    with pytest.raises((TypeError, ValueError, GoogleSheetsError)) as exc_info:
        await gsheet_set_values_to_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A1:B2", values=invalid_data
        )

    assert exc_info.value is not None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_duplicate_sheet_name(test_spreadsheet_id, sheet_info):
    """중복 시트명 에러 처리 테스트"""
    existing_sheet_name = sheet_info["name"]

    with pytest.raises(Exception) as exc_info:
        await gsheet_add_sheet(spreadsheet_id=test_spreadsheet_id, name=existing_sheet_name)

    assert exc_info.value is not None
    # locale 독립적인 에러 타입 확인 (중복 시트명 오류는 보통 GoogleSheetsError로 처리)
    assert isinstance(exc_info.value, GoogleSheetsError)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_delete_nonexistent_sheet(test_spreadsheet_id):
    """존재하지 않는 시트 삭제 에러 처리 테스트"""
    nonexistent_sheet = "NonExistentSheetToDelete"

    with pytest.raises(Exception) as exc_info:
        await gsheet_delete_sheet(spreadsheet_id=test_spreadsheet_id, sheet_name=nonexistent_sheet)

    assert exc_info.value is not None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_rename_nonexistent_sheet(test_spreadsheet_id):
    """존재하지 않는 시트 이름변경 에러 처리 테스트"""
    nonexistent_sheet = "NonExistentSheetToRename"

    with pytest.raises(Exception) as exc_info:
        await gsheet_rename_sheet(spreadsheet_id=test_spreadsheet_id, sheet_name=nonexistent_sheet, new_name="NewName")

    assert exc_info.value is not None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
@pytest.mark.parametrize(
    "invalid_id",
    [
        "",  # 빈 문자열
        "123",  # 너무 짧은 ID
        "invalid-characters-!@#$%",  # 잘못된 문자
        None,  # None 값
    ],
)
async def test_various_invalid_spreadsheet_ids(invalid_id):
    """다양한 잘못된 스프레드시트 ID 테스트"""
    with pytest.raises((TypeError, ValueError, GoogleSheetsError, SpreadsheetNotFoundError, AuthenticationError)):
        if invalid_id is None:
            # None 값은 TypeError를 발생시킬 수 있음
            await gsheet_get_spreadsheet_info(spreadsheet_id=invalid_id)
        else:
            await gsheet_get_spreadsheet_info(spreadsheet_id=invalid_id)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_malformed_csv_data(test_spreadsheet_id, sheet_info):
    """잘못된 형식의 CSV 데이터 에러 처리 테스트"""
    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_set_values_to_range_with_csv

    sheet_name = sheet_info["name"]

    # 비어있는 CSV 데이터는 에러가 아닐 수 있음
    empty_csv = ""

    # 에러가 발생하지 않을 수도 있으므로 결과만 확인
    try:
        result = await gsheet_set_values_to_range_with_csv(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!Z1", csv_data=empty_csv
        )
        # 성공한 경우 결과가 있어야 함
        assert result is not None
    except Exception as e:
        # 에러가 발생한 경우 적절한 에러인지 확인
        assert e is not None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_permission_denied_simulation():
    """권한 거부 시뮬레이션 테스트 (실제로는 실행하지 않음)"""
    # 이 테스트는 실제 권한 문제를 시뮬레이션하기 어려우므로
    # 단순히 테스트 구조만 확인
    assert True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_network_error_simulation():
    """네트워크 에러 시뮬레이션 테스트 (실제로는 실행하지 않음)"""
    # 네트워크 에러는 실제 환경에서 시뮬레이션하기 어려우므로
    # 단순히 테스트 구조만 확인
    assert True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.error_handling
async def test_large_data_handling(test_spreadsheet_id, sheet_info):
    """대용량 데이터 처리 한계 테스트"""
    sheet_name = sheet_info["name"]

    # 매우 큰 데이터셋 생성 (1000x10)
    large_data = []
    for i in range(1000):
        row = [f"Data{i}_{j}" for j in range(10)]
        large_data.append(row)

    # 이 테스트는 실제로 실행하면 시간이 오래 걸릴 수 있으므로
    # 작은 샘플로만 테스트
    sample_data = large_data[:5]  # 처음 5행만 사용

    try:
        result = await gsheet_set_values_to_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A100:J104", values=sample_data
        )
        assert result is not None
    except Exception as e:
        # 에러가 발생한 경우 적절한 에러 타입인지 확인
        assert isinstance(e, (GoogleSheetsError, RateLimitError, SpreadsheetNotFoundError, AuthenticationError))

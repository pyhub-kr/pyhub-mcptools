"""Google Sheets 기본 작업 테스트"""

import json

import pytest

from pyhub.mcptools.google.sheets.tools.sheets import (
    gsheet_add_sheet,
    gsheet_clear_values_from_range,
    gsheet_delete_sheet,
    gsheet_get_spreadsheet_info,
    gsheet_get_values_from_range,
    gsheet_list_spreadsheets,
    gsheet_rename_sheet,
    gsheet_search_by_name,
    gsheet_set_values_to_range,
    gsheet_set_values_to_range_with_csv,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_spreadsheets():
    """스프레드시트 목록 조회 테스트"""
    result = await gsheet_list_spreadsheets()
    data = json.loads(result)

    assert "spreadsheets" in data
    assert isinstance(data["spreadsheets"], list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_spreadsheets():
    """스프레드시트 검색 테스트"""
    result = await gsheet_search_by_name(search_term="pytest", exact_match=False)
    data = json.loads(result)

    assert "matches" in data
    assert isinstance(data["matches"], list)
    assert "total" in data
    assert "search_term" in data
    assert data["search_term"] == "pytest"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_spreadsheet_info(test_spreadsheet_id):
    """스프레드시트 정보 조회 테스트"""
    result = await gsheet_get_spreadsheet_info(spreadsheet_id=test_spreadsheet_id)
    data = json.loads(result)

    assert "id" in data
    assert "name" in data
    assert "url" in data
    assert "sheets" in data
    assert len(data["sheets"]) > 0
    assert data["id"] == test_spreadsheet_id

    # 첫 번째 시트 정보 확인
    first_sheet = data["sheets"][0]
    assert "id" in first_sheet
    assert "name" in first_sheet
    assert "index" in first_sheet
    assert "rowCount" in first_sheet
    assert "columnCount" in first_sheet


@pytest.mark.asyncio
@pytest.mark.integration
async def test_write_and_read_data(test_spreadsheet_id, sheet_info, sample_data):
    """데이터 쓰기 및 읽기 테스트"""
    sheet_name = sheet_info["name"]

    # 데이터 쓰기
    write_result = await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A1:C4", values=sample_data
    )
    write_data = json.loads(write_result)

    assert "updatedCells" in write_data
    assert write_data["updatedCells"] > 0
    assert "updatedRows" in write_data
    assert "updatedColumns" in write_data
    assert "updatedRange" in write_data

    # 데이터 읽기
    read_result = await gsheet_get_values_from_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A1:C4"
    )
    read_data = json.loads(read_result)

    assert "values" in read_data
    assert "range" in read_data
    assert "rowCount" in read_data
    assert "columnCount" in read_data
    assert read_data["values"] == sample_data
    assert read_data["rowCount"] == len(sample_data)
    assert read_data["columnCount"] == len(sample_data[0])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_csv_write(test_spreadsheet_id, sheet_info, sample_csv_data):
    """CSV 데이터 쓰기 테스트"""
    sheet_name = sheet_info["name"]

    result = await gsheet_set_values_to_range_with_csv(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!E1", csv_data=sample_csv_data
    )
    data = json.loads(result)

    assert "updatedCells" in data
    assert data["updatedCells"] > 0
    assert "updatedRows" in data
    assert "updatedColumns" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_expand_mode(test_spreadsheet_id, sheet_info):
    """확장 모드 테스트"""
    sheet_name = sheet_info["name"]

    # table 확장 모드로 데이터 읽기
    result = await gsheet_get_values_from_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A1", expand_mode="table"
    )
    data = json.loads(result)

    assert "values" in data
    assert "range" in data
    assert "rowCount" in data
    assert "columnCount" in data
    assert "expand_mode" in data
    assert data["expand_mode"] == "table"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_clear_values(test_spreadsheet_id, sheet_info):
    """값 삭제 테스트"""
    sheet_name = sheet_info["name"]

    # 특정 범위 삭제
    result = await gsheet_clear_values_from_range(spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!F1:H5")
    data = json.loads(result)

    assert "clearedRange" in data
    assert data["clearedRange"] == f"{sheet_name}!F1:H5"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sheet_operations(test_spreadsheet_id):
    """시트 작업 테스트 (추가, 이름변경, 삭제)"""
    # 새 시트 추가
    add_result = await gsheet_add_sheet(spreadsheet_id=test_spreadsheet_id, name="PytestTestSheet")
    add_data = json.loads(add_result)

    assert "id" in add_data
    assert "name" in add_data
    assert "index" in add_data
    assert add_data["name"] == "PytestTestSheet"

    # 시트 이름 변경
    rename_result = await gsheet_rename_sheet(
        spreadsheet_id=test_spreadsheet_id, sheet_name="PytestTestSheet", new_name="RenamedPytestSheet"
    )
    rename_data = json.loads(rename_result)

    assert "id" in rename_data
    assert "name" in rename_data
    assert "index" in rename_data
    assert rename_data["name"] == "RenamedPytestSheet"

    # 시트 삭제
    delete_result = await gsheet_delete_sheet(spreadsheet_id=test_spreadsheet_id, sheet_name="RenamedPytestSheet")
    delete_data = json.loads(delete_result)

    assert "success" in delete_data
    assert delete_data["success"] is True
    assert "message" in delete_data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("expand_mode", ["table", "down", "right"])
async def test_expand_modes(test_spreadsheet_id, sheet_info, sample_data, expand_mode):
    """다양한 확장 모드 테스트"""
    sheet_name = sheet_info["name"]

    # 먼저 테스트 데이터 입력
    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A10:C13", values=sample_data
    )

    # 확장 모드로 읽기
    result = await gsheet_get_values_from_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A10", expand_mode=expand_mode
    )
    data = json.loads(result)

    assert "values" in data
    assert "expand_mode" in data
    assert data["expand_mode"] == expand_mode
    assert len(data["values"]) > 0

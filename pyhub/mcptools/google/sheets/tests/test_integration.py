"""Google Sheets 통합 테스트 - 전체 워크플로우 테스트"""

import asyncio
import json

import pytest

from pyhub.mcptools.google.sheets.tools.sheets import (
    gsheet_add_sheet,
    gsheet_create_spreadsheet,
    gsheet_get_spreadsheet_info,
    gsheet_get_values_from_range,
    gsheet_rename_sheet,
    gsheet_set_values_to_range,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_spreadsheet_workflow():
    """완전한 스프레드시트 워크플로우 테스트 - 생성부터 삭제까지"""
    from datetime import datetime

    # 1. 새 스프레드시트 생성
    workflow_name = f"Integration-Test-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    create_result = await gsheet_create_spreadsheet(name=workflow_name)
    create_data = json.loads(create_result)

    assert "id" in create_data
    spreadsheet_id = create_data["id"]

    try:
        # 2. 스프레드시트 정보 확인
        info_result = await gsheet_get_spreadsheet_info(spreadsheet_id=spreadsheet_id)
        info_data = json.loads(info_result)
        assert len(info_data["sheets"]) == 1
        default_sheet_name = info_data["sheets"][0]["name"]

        # 3. 데이터 입력
        test_data = [
            ["Product", "Price", "Quantity", "Total"],
            ["Laptop", "1000", "2", "2000"],
            ["Mouse", "50", "10", "500"],
            ["Keyboard", "100", "5", "500"],
        ]

        write_result = await gsheet_set_values_to_range(
            spreadsheet_id=spreadsheet_id, sheet_range=f"{default_sheet_name}!A1:D4", values=test_data
        )
        write_data = json.loads(write_result)
        assert write_data["updatedCells"] == 16

        # 4. 데이터 읽기 및 검증
        read_result = await gsheet_get_values_from_range(
            spreadsheet_id=spreadsheet_id, sheet_range=f"{default_sheet_name}!A1:D4"
        )
        read_data = json.loads(read_result)
        assert read_data["values"] == test_data

        # 5. 새 시트 추가
        add_sheet_result = await gsheet_add_sheet(spreadsheet_id=spreadsheet_id, name="Summary")
        add_sheet_data = json.loads(add_sheet_result)
        assert add_sheet_data["name"] == "Summary"

        # 6. 요약 데이터 입력
        summary_data = [
            ["Metric", "Value"],
            ["Total Products", "3"],
            ["Total Revenue", "3000"],
            ["Average Price", "383.33"],
        ]

        await gsheet_set_values_to_range(
            spreadsheet_id=spreadsheet_id, sheet_range="Summary!A1:B4", values=summary_data
        )

        # 7. 시트 이름 변경
        rename_result = await gsheet_rename_sheet(
            spreadsheet_id=spreadsheet_id, sheet_name="Summary", new_name="Financial_Summary"
        )
        rename_data = json.loads(rename_result)
        assert rename_data["name"] == "Financial_Summary"

        # 8. 최종 검증 - 모든 데이터가 올바르게 있는지 확인
        final_info = await gsheet_get_spreadsheet_info(spreadsheet_id=spreadsheet_id)
        final_data = json.loads(final_info)

        assert len(final_data["sheets"]) == 2
        sheet_names = [sheet["name"] for sheet in final_data["sheets"]]
        assert "Financial_Summary" in sheet_names

        # 원본 데이터 재확인
        final_read = await gsheet_get_values_from_range(
            spreadsheet_id=spreadsheet_id, sheet_range=f"{default_sheet_name}!A1:D4"
        )
        final_read_data = json.loads(final_read)
        assert final_read_data["values"] == test_data

        # 요약 데이터 재확인
        summary_read = await gsheet_get_values_from_range(
            spreadsheet_id=spreadsheet_id, sheet_range="Financial_Summary!A1:B4"
        )
        summary_read_data = json.loads(summary_read)
        assert summary_read_data["values"] == summary_data

        print("✅ Integration test completed successfully!")
        print(f"Spreadsheet: {workflow_name}")
        print(f"URL: {create_data['url']}")

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise

    finally:
        # 정리는 수동으로 진행 (Google Drive에서 삭제)
        print(f"Note: Please manually delete test spreadsheet: {workflow_name}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_data_validation_workflow(test_spreadsheet_id, sheet_info):
    """데이터 검증 워크플로우 테스트"""
    sheet_name = sheet_info["name"]

    # 1. 다양한 데이터 타입 입력
    mixed_data = [
        ["String", "Number", "Boolean", "Formula"],
        ["Hello", "123", "TRUE", "=B2*2"],
        ["World", "456.78", "FALSE", "=B3*2"],
        ["Test", "0", "TRUE", "=SUM(B2:B4)"],
    ]

    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A10:D13", values=mixed_data
    )

    # 2. 데이터 읽기 및 타입 확인
    read_result = await gsheet_get_values_from_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A10:D13"
    )
    read_data = json.loads(read_result)

    # 기본 구조 검증
    assert len(read_data["values"]) == 4
    assert len(read_data["values"][0]) == 4

    # 헤더 검증
    headers = read_data["values"][0]
    assert headers == ["String", "Number", "Boolean", "Formula"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_large_dataset_workflow(test_spreadsheet_id, sheet_info):
    """대용량 데이터셋 워크플로우 테스트"""
    sheet_name = sheet_info["name"]

    # 100행의 테스트 데이터 생성
    large_dataset = [["ID", "Name", "Email", "Department", "Salary"]]

    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance"]
    for i in range(1, 101):
        row = [
            str(i),
            f"Employee_{i:03d}",
            f"emp{i:03d}@company.com",
            departments[i % len(departments)],
            str(50000 + (i * 1000)),
        ]
        large_dataset.append(row)

    # 대용량 데이터 입력
    write_result = await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A20:E120", values=large_dataset
    )
    write_data = json.loads(write_result)

    assert write_data["updatedCells"] == 505  # 101 rows * 5 columns
    assert write_data["updatedRows"] == 101
    assert write_data["updatedColumns"] == 5

    # 부분 데이터 읽기 테스트
    partial_read = await gsheet_get_values_from_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A20:E25"  # 첫 6행만
    )
    partial_data = json.loads(partial_read)

    assert len(partial_data["values"]) == 6
    assert partial_data["values"][0] == ["ID", "Name", "Email", "Department", "Salary"]
    assert partial_data["values"][1][0] == "1"  # 첫 번째 직원 ID


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_operations(test_spreadsheet_id, sheet_info):
    """동시 작업 테스트"""
    import asyncio

    sheet_name = sheet_info["name"]

    # 여러 영역에 동시에 데이터 쓰기
    async def write_section(section_id, start_row):
        data = [
            [f"Section_{section_id}", "Data", "Test"],
            [f"Row1_{section_id}", "Value1", "Test1"],
            [f"Row2_{section_id}", "Value2", "Test2"],
        ]

        await gsheet_set_values_to_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A{start_row}:C{start_row+2}", values=data
        )
        return section_id

    # 3개 섹션을 동시에 작성
    tasks = [
        write_section(1, 200),
        write_section(2, 210),
        write_section(3, 220),
    ]

    results = await asyncio.gather(*tasks)
    assert len(results) == 3
    assert set(results) == {1, 2, 3}

    # 결과 검증
    for i, section_id in enumerate(results, 1):
        start_row = 190 + (i * 10)
        read_result = await gsheet_get_values_from_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A{start_row}:C{start_row+2}"
        )
        read_data = json.loads(read_result)

        assert len(read_data["values"]) == 3
        assert read_data["values"][0][0] == f"Section_{section_id}"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_stress_test_operations(test_spreadsheet_id, sheet_info):
    """스트레스 테스트 - 반복적인 작업"""
    sheet_name = sheet_info["name"]

    # 50번의 작은 쓰기 작업 수행
    for i in range(50):
        data = [[f"Iteration_{i}", f"Value_{i}", str(i * 10)]]

        await gsheet_set_values_to_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A{300+i}:C{300+i}", values=data
        )

        # 작업 간 짧은 지연
        await asyncio.sleep(0.1)

    # 결과 검증 - 몇 개의 샘플만 확인
    sample_indices = [0, 24, 49]  # 첫 번째, 중간, 마지막

    for idx in sample_indices:
        read_result = await gsheet_get_values_from_range(
            spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A{300+idx}:C{300+idx}"
        )
        read_data = json.loads(read_result)

        assert len(read_data["values"]) == 1
        assert read_data["values"][0][0] == f"Iteration_{idx}"
        assert read_data["values"][0][1] == f"Value_{idx}"
        assert read_data["values"][0][2] == str(idx * 10)

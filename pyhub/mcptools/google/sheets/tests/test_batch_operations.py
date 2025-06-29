"""Google Sheets 배치 작업 테스트"""

import json

import pytest

# 배치 도구 import 시도
try:
    from pyhub.mcptools.google.sheets.tools.sheets_batch import (
        gsheet_batch_clear,
        gsheet_batch_copy,
        gsheet_batch_read,
        gsheet_batch_write,
    )

    BATCH_TOOLS_AVAILABLE = True
except ImportError:
    BATCH_TOOLS_AVAILABLE = False

# 청크 도구 import 시도
try:
    from pyhub.mcptools.google.sheets.tools.sheets_chunked import (
        gsheet_read_chunked,
        gsheet_write_chunked,
    )

    CHUNKED_TOOLS_AVAILABLE = True
except ImportError:
    CHUNKED_TOOLS_AVAILABLE = False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.batch
@pytest.mark.skipif(not BATCH_TOOLS_AVAILABLE, reason="Batch tools not available")
async def test_batch_read(test_spreadsheet_id, sheet_info, sample_data):
    """배치 읽기 테스트"""
    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_set_values_to_range

    sheet_name = sheet_info["name"]

    # 테스트 데이터 준비
    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A1:C4", values=sample_data
    )

    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!E1:G4", values=sample_data
    )

    # 배치 읽기 실행
    ranges = [f"{sheet_name}!A1:C4", f"{sheet_name}!E1:G4"]
    result = await gsheet_batch_read(spreadsheet_id=test_spreadsheet_id, ranges=ranges)
    data = json.loads(result)

    assert "ranges" in data
    assert "total_ranges" in data
    assert "total_cells" in data
    assert data["total_ranges"] == 2
    assert len(data["ranges"]) == 2

    # 각 범위의 데이터 확인
    for range_data in data["ranges"]:
        assert "range" in range_data
        assert "values" in range_data
        assert "row_count" in range_data
        assert "column_count" in range_data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.batch
@pytest.mark.skipif(not BATCH_TOOLS_AVAILABLE, reason="Batch tools not available")
async def test_batch_write(test_spreadsheet_id, sheet_info):
    """배치 쓰기 테스트"""
    sheet_name = sheet_info["name"]

    # 배치 업데이트 데이터 준비
    updates = [
        {"range": f"{sheet_name}!A20:B21", "values": [["Batch", "Test"], ["Data", "123"]]},
        {"range": f"{sheet_name}!D20:E21", "values": [["More", "Batch"], ["Test", "456"]]},
    ]

    # 배치 쓰기 실행
    result = await gsheet_batch_write(spreadsheet_id=test_spreadsheet_id, updates=updates)
    data = json.loads(result)

    assert "ranges_updated" in data
    assert "total_cells_updated" in data
    assert "spreadsheet_id" in data
    assert data["ranges_updated"] == 2
    assert data["spreadsheet_id"] == test_spreadsheet_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.batch
@pytest.mark.skipif(not BATCH_TOOLS_AVAILABLE, reason="Batch tools not available")
async def test_batch_clear(test_spreadsheet_id, sheet_info, sample_data):
    """배치 삭제 테스트"""
    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_set_values_to_range

    sheet_name = sheet_info["name"]

    # 삭제할 데이터 먼저 입력
    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A30:C33", values=sample_data
    )

    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!E30:G33", values=sample_data
    )

    # 배치 삭제 실행
    ranges = [f"{sheet_name}!A30:C33", f"{sheet_name}!E30:G33"]
    result = await gsheet_batch_clear(spreadsheet_id=test_spreadsheet_id, ranges=ranges)
    data = json.loads(result)

    assert "cleared_ranges" in data
    assert "spreadsheet_id" in data
    assert data["spreadsheet_id"] == test_spreadsheet_id
    assert len(data["cleared_ranges"]) == 2


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.batch
@pytest.mark.skipif(not BATCH_TOOLS_AVAILABLE, reason="Batch tools not available")
async def test_batch_copy(test_spreadsheet_id, sheet_info, sample_data):
    """배치 복사 테스트"""
    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_set_values_to_range

    sheet_name = sheet_info["name"]

    # 복사할 데이터 먼저 입력
    await gsheet_set_values_to_range(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A40:C43", values=sample_data
    )

    # 배치 복사 설정
    copy_operations = [
        {"source_range": f"{sheet_name}!A40:C43", "destination_range": f"{sheet_name}!E40:G43"},
        {"source_range": f"{sheet_name}!A40:C43", "destination_range": f"{sheet_name}!I40:K43"},
    ]

    # 배치 복사 실행
    result = await gsheet_batch_copy(spreadsheet_id=test_spreadsheet_id, copy_operations=copy_operations)
    data = json.loads(result)

    assert "operations_completed" in data
    assert "spreadsheet_id" in data
    assert data["operations_completed"] == 2
    assert data["spreadsheet_id"] == test_spreadsheet_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not CHUNKED_TOOLS_AVAILABLE, reason="Chunked tools not available")
async def test_chunked_write(test_spreadsheet_id, sheet_info):
    """청크 단위 쓰기 테스트"""
    sheet_name = sheet_info["name"]

    # 큰 데이터셋 생성 (100행)
    large_data = []
    for i in range(100):
        large_data.append([f"Row{i+1}", f"Data{i+1}", f"Value{i+1}"])

    # 청크 쓰기 실행 (10행씩 나누어서)
    result = await gsheet_write_chunked(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A50:C149", values=large_data, chunk_size=10
    )
    data = json.loads(result)

    assert "total_chunks" in data
    assert "total_rows_written" in data
    assert "chunk_size" in data
    assert data["total_rows_written"] == 100
    assert data["chunk_size"] == 10
    assert data["total_chunks"] == 10


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not CHUNKED_TOOLS_AVAILABLE, reason="Chunked tools not available")
async def test_chunked_read(test_spreadsheet_id, sheet_info):
    """청크 단위 읽기 테스트"""
    sheet_name = sheet_info["name"]

    # 청크 읽기 실행
    result = await gsheet_read_chunked(
        spreadsheet_id=test_spreadsheet_id, sheet_range=f"{sheet_name}!A50:C149", chunk_size=20
    )
    data = json.loads(result)

    assert "total_chunks" in data
    assert "total_rows_read" in data
    assert "chunk_size" in data
    assert "chunks" in data
    assert data["chunk_size"] == 20

    # 각 청크 데이터 확인
    for chunk in data["chunks"]:
        assert "chunk_index" in chunk
        assert "values" in chunk
        assert "row_count" in chunk

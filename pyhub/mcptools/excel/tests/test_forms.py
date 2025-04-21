from unittest.mock import MagicMock

import pytest

from pyhub.mcptools.excel.forms import PivotTableCreateForm
from pyhub.mcptools.excel.types import ExcelAggregationType

# Test Data
SOURCE_COLUMNS = ["지역", "매장", "제품카테고리", "판매수량", "수량", "가격", "날짜"]


@pytest.fixture
def mock_ranges():
    """Mock Range 객체를 생성하는 fixture"""
    source_range = MagicMock()
    dest_range = MagicMock()
    source_range.__getitem__.return_value.expand.return_value.value = SOURCE_COLUMNS
    return source_range, dest_range


@pytest.mark.parametrize(
    "form_data,expected_data",
    [
        (
            {
                "row_field_names": "지역,매장",
                "column_field_names": "제품카테고리",
                "page_field_names": "",
                "value_fields": "판매수량:SUM|수량:SUM",
                "pivot_table_name": "테스트_피벗테이블",
            },
            {
                "row_field_names": ["지역", "매장"],
                "column_field_names": ["제품카테고리"],
                "page_field_names": [],
                "value_fields": [
                    {"field_name": "판매수량", "agg_func": ExcelAggregationType.SUM},
                    {"field_name": "수량", "agg_func": ExcelAggregationType.SUM},
                ],
            },
        ),
        (
            {
                "row_field_names": "지역",
                "column_field_names": "제품카테고리",
                "page_field_names": "날짜",
                "value_fields": "판매수량:SUM",
                "pivot_table_name": "단일_피벗",
            },
            {
                "row_field_names": ["지역"],
                "column_field_names": ["제품카테고리"],
                "page_field_names": ["날짜"],
                "value_fields": [
                    {"field_name": "판매수량", "agg_func": ExcelAggregationType.SUM},
                ],
            },
        ),
    ],
)
def test_valid_form(mock_ranges, form_data, expected_data):
    """유효한 데이터로 폼 검증"""

    source_range, dest_range = mock_ranges
    form = PivotTableCreateForm(data=form_data, source_range=source_range, dest_range=dest_range)

    assert form.is_valid()
    assert form.cleaned_data["row_field_names"] == expected_data["row_field_names"]
    assert form.cleaned_data["column_field_names"] == expected_data["column_field_names"]
    assert form.cleaned_data["page_field_names"] == expected_data["page_field_names"]
    assert form.cleaned_data["value_fields"] == expected_data["value_fields"]


@pytest.mark.parametrize(
    "invalid_data,expected_error",
    [
        (
            {
                "row_field_names": "지역,존재하지않는필드",
                "column_field_names": "제품카테고리",
                "value_fields": "판매수량:SUM",
            },
            "Row fields contain invalid field names",
        ),
        (
            {
                "row_field_names": "지역,매장",
                "column_field_names": "제품카테고리",
                "value_fields": "존재하지않는필드:SUM",
            },
            "value_fields contain invalid field name",
        ),
        (
            {
                "row_field_names": "지역",
                "column_field_names": "제품카테고리",
                "value_fields": "판매수량:INVALID",  # 잘못된 집계 함수
            },
            "Invalid aggregation function",
        ),
        (
            {
                "row_field_names": "",  # 빈 row_field_names
                "column_field_names": "제품카테고리",
                "value_fields": "판매수량:SUM",
            },
            "This field is required.",
        ),
    ],
)
def test_invalid_forms(mock_ranges, invalid_data, expected_error):
    """유효하지 않은 데이터로 폼 검증"""
    source_range, dest_range = mock_ranges
    form = PivotTableCreateForm(data=invalid_data, source_range=source_range, dest_range=dest_range)

    assert not form.is_valid()
    assert expected_error in str(form.errors)


@pytest.mark.parametrize(
    "form_data,expected_value_fields",
    [
        (
            {"row_field_names": "지역", "value_fields": "판매수량:SUM|수량:COUNT"},
            [
                {"field_name": "판매수량", "agg_func": ExcelAggregationType.SUM},
                {"field_name": "수량", "agg_func": ExcelAggregationType.COUNT},
            ],
        ),
        (
            {"row_field_names": "지역", "value_fields": "판매수량:SUM|가격:AVERAGE"},
            [
                {"field_name": "판매수량", "agg_func": ExcelAggregationType.SUM},
                {"field_name": "가격", "agg_func": ExcelAggregationType.AVERAGE},
            ],
        ),
    ],
)
def test_value_fields_parsing(mock_ranges, form_data, expected_value_fields):
    """값 필드 파싱 테스트"""
    source_range, dest_range = mock_ranges
    form = PivotTableCreateForm(data=form_data, source_range=source_range, dest_range=dest_range)

    assert form.is_valid()
    value_fields_list = form.cleaned_data["value_fields"]
    assert value_fields_list == expected_value_fields

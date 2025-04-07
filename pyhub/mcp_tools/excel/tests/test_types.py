import pytest
from pyhub.mcp_tools.excel.types import validate_excel_range


@pytest.mark.parametrize(
    "value,expected",
    [
        ("A1", "A1"),  # 기본 셀 참조
        ("$A$1", "$A$1"),  # 절대 참조
        ("A1:B2", "A1:B2"),  # 셀 범위
        ("$A$1:$B$2", "$A$1:$B$2"),  # 절대 참조 범위
        ("Sheet1!A1", "Sheet1!A1"),  # 시트명 포함
        ("'My Sheet'!A1", "'My Sheet'!A1"),  # 공백 포함 시트명
        ("Sheet1!$A$1:$B$2", "Sheet1!$A$1:$B$2"),  # 시트명과 절대 참조 범위
        ("'My Sheet'!$A$1:$B$2", "'My Sheet'!$A$1:$B$2"),  # 공백 포함 시트명과 절대 참조 범위
        (None, None),  # None 입력
    ],
)
def test_validate_excel_range_valid_inputs(value, expected):
    assert validate_excel_range(value) == expected


@pytest.mark.parametrize(
    "invalid_value",
    [
        "A",  # 열만 있는 경우
        "1",  # 행만 있는 경우
        "A1:",  # 불완전한 범위
        ":B2",  # 불완전한 범위
        "A1:B",  # 불완전한 범위
        "Sheet1",  # 시트명만 있는 경우
        "Sheet1!",  # 시트명과 구분자만 있는 경우
        "'Sheet1",  # 닫히지 않은 따옴표
        "Sheet1'!A1",  # 잘못된 따옴표 위치
        "AA99999999",  # 너무 큰 행 번호
        "XFD99999999",  # 엑셀 최대 범위 초과
    ],
)
def test_validate_excel_range_invalid_inputs(invalid_value):
    with pytest.raises(ValueError):
        validate_excel_range(invalid_value)
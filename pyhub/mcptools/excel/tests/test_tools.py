import pytest

from pyhub.mcptools.excel.tools import fix_data


@pytest.mark.parametrize(
    "sheet_range,values,expected",
    [
        # 문자열 입력은 그대로 반환
        ("A1:A10", "test string", "test string"),
        
        # 리스트가 아닌 입력은 그대로 반환 
        ("A1:A10", 123, 123),
        
        # 이미 중첩 리스트인 경우 그대로 반환
        ("A1:A10", [["v1"], ["v2"]], [["v1"], ["v2"]]),
        
        # 유효하지 않은 범위 패턴은 값을 그대로 반환
        ("invalid_range", ["v1", "v2"], ["v1", "v2"]),
        
        # 단일 셀 범위는 값을 그대로 반환
        ("A1", ["v1", "v2"], ["v1", "v2"]),
        
        # 열 방향 범위(같은 열, 다른 행)에 대해 중첩 리스트로 변환
        ("A1:A3", ["v1", "v2", "v3"], [["v1"], ["v2"], ["v3"]]),
        ("Sheet1!B2:B5", ["v1", "v2", "v3", "v4"], [["v1"], ["v2"], ["v3"], ["v4"]]),
        ("$C$1:$C$3", ["v1", "v2", "v3"], [["v1"], ["v2"], ["v3"]]),
        
        # 행 방향 범위(다른 열, 같은 행)는 그대로 반환
        ("A1:C1", ["v1", "v2", "v3"], ["v1", "v2", "v3"]),
        ("Sheet1!B2:D2", ["v1", "v2", "v3"], ["v1", "v2", "v3"]),
        
        # 빈 리스트는 그대로 반환
        ("A1:A10", [], []),
    ]
)
def test_fix_data(sheet_range, values, expected):
    assert fix_data(sheet_range, values) == expected

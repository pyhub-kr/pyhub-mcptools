import pytest

from pyhub.mcptools.excel.tools import fix_data
from pyhub.mcptools.excel.utils import json_loads, csv_loads


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
    ],
)
def test_fix_data(sheet_range, values, expected):
    assert fix_data(sheet_range, values) == expected


@pytest.mark.parametrize(
    "json_str,expected",
    [
        # 유효한 JSON 문자열
        ('{"key": "value"}', {"key": "value"}),
        ('["item1", "item2"]', ["item1", "item2"]),
        ('{"numbers": [1, 2, 3]}', {"numbers": [1, 2, 3]}),
        # Python 리터럴 형식 (literal_eval로 처리 가능)
        ("{'key': 'value'}", {"key": "value"}),
        ("['item1', 'item2']", ["item1", "item2"]),
        # JSON이 아닌 문자열은 그대로 반환
        ("invalid json", "invalid json"),
        # 비문자열 입력은 그대로 반환
        (123, 123),
        (None, None),
        ([1, 2, 3], [1, 2, 3]),
    ],
)
def test_json_loads(json_str, expected):
    assert json_loads(json_str) == expected


@pytest.mark.parametrize(
    "csv_str,expected",
    [
        # 기본 CSV 문자열
        ("v1,v2,v3", [["v1", "v2", "v3"]]),
        ("v1,v2,v3\nv4,v5,v6", [["v1", "v2", "v3"], ["v4", "v5", "v6"]]),
        # 따옴표로 묶인 값 (쉼표 포함)
        ('"v1,with,comma",v2,v3', [["v1,with,comma", "v2", "v3"]]),
        # 빈 셀 처리
        ("v1,,v3", [["v1", "", "v3"]]),
        ("v1,v2,v3\n,,", [["v1", "v2", "v3"], ["", "", ""]]),
        # 공백 문자열
        ("", [[""]]),
        # 단일 값
        ("single", [["single"]]),
    ],
)
def test_csv_loads(csv_str, expected):
    assert csv_loads(csv_str) == expected

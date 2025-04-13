import pytest

from pyhub.mcptools.excel.types import validate_excel_range, validate_formula


@pytest.mark.parametrize(
    "value,expected",
    [
        ("A1", "A1"),  # 기본 셀 참조
        ("A:C", "A:C"),
        ("$A$1", "$A$1"),  # 절대 참조
        ("A1:B2", "A1:B2"),  # 셀 범위
        ("$A$1:$B$2", "$A$1:$B$2"),  # 절대 참조 범위
        ("Sheet1!A1", "Sheet1!A1"),  # 시트명 포함
        ("'My Sheet'!A1", "'My Sheet'!A1"),  # 공백 포함 시트명
        ("Sheet1!$A$1:$B$2", "Sheet1!$A$1:$B$2"),  # 시트명과 절대 참조 범위
        ("'My Sheet'!$A$1:$B$2", "'My Sheet'!$A$1:$B$2"),  # 공백 포함 시트명과 절대 참조 범위
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


@pytest.mark.parametrize(
    "value,expected",
    [
        ("=A1", "=A1"),  # 기본 셀 참조
        ("=123", "=123"),  # 숫자 리터럴
        ('="text"', '="text"'),  # 문자열 리터럴
        ("=A1+B1", "=A1+B1"),  # 덧셈 연산
        ("=C1*D1", "=C1*D1"),  # 곱셈 연산
        ("=E1/F1", "=E1/F1"),  # 나눗셈 연산
        ("=SUM(A1:A10)", "=SUM(A1:A10)"),  # 함수 호출
        ("=AVERAGE(B1:B5)", "=AVERAGE(B1:B5)"),  # 평균 함수
        ("=IF(A1>0, SUM(B1:B5), 0)", "=IF(A1>0, SUM(B1:B5), 0)"),  # 중첩 함수
        ('=CONCATENATE(A1, " ", B1)', '=CONCATENATE(A1, " ", B1)'),  # 문자열 결합
        ("=Sheet1!A1", "=Sheet1!A1"),  # 시트 참조
        ("='My Sheet'!B2", "='My Sheet'!B2"),  # 공백 포함 시트 참조
    ],
)
def test_validate_formula_valid_inputs(value, expected):
    assert validate_formula(value) == expected


@pytest.mark.parametrize(
    "invalid_value",
    [
        "A1",  # = 없음
        "=",  # = 만 있음
        "=(A1",  # 괄호 짝이 맞지 않음
        "=A1)",  # 괄호 짝이 맞지 않음
        "=SUM(A1:A10))",  # 괄호 개수 불일치
        "=@Invalid(A1)",  # 잘못된 함수명
        '="unclosed',  # 닫히지 않은 문자열
        "=Sheet1!",  # 불완전한 시트 참조
        "='Sheet1!A1",  # 잘못된 따옴표
    ],
)
def test_validate_formula_invalid_inputs(invalid_value):
    with pytest.raises(ValueError):
        validate_formula(invalid_value)

import re


def validate_excel_range(value: str) -> str:
    """Excel 범위 형식을 검증하는 함수 (시트 이름, 절대/상대 참조 포함)"""

    # 셀 주소 부분 (예: $A$1, A1)
    cell_pattern = r"\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}"
    # 시트 이름 부분 (예: Sheet1!, 'My Sheet'!) - 선택 사항
    # 시트 이름에 공백이나 특수 문자가 포함될 경우 작은따옴표로 묶습니다.
    sheet_pattern = r"(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?"

    # 단일 셀 또는 셀 범위 검증을 위한 정규 표현식
    # 예: Sheet1!A1, 'My Sheet'!$B$2, C3, $D$4:$E$5, Sheet2!F6:G7
    full_range_pattern = f"^{sheet_pattern}{cell_pattern}(?::{cell_pattern})?$"

    if not re.match(full_range_pattern, value, re.IGNORECASE):
        raise ValueError(
            f"유효하지 않은 Excel 범위 형식입니다: {value}. "
            f"예시: 'A1', 'A1:C3', 'Sheet1!A1', '$A$1', 'Sheet Name'!$B$2:$C$10"
        )

    return value


def validate_formula(value: str) -> str:
    """Excel 수식 형식을 검증하는 함수

    지원하는 수식 패턴:
    1. 기본 수식: =A1, =123, ="text"
    2. 수식 연산: =A1+B1, =C1*D1, =E1/F1
    3. 함수 호출: =SUM(A1:A10), =AVERAGE(B1:B5)
    4. 중첩 함수: =IF(A1>0, SUM(B1:B5), 0)
    5. 문자열 결합: =CONCATENATE(A1, " ", B1)
    6. 참조 수식: =Sheet1!A1, ='My Sheet'!B2

    Args:
        value (str): 검증할 Excel 수식 문자열

    Returns:
        str: 검증된 수식 문자열

    Raises:
        ValueError: 유효하지 않은 수식 형식일 경우
    """

    value = value.strip()

    if not value.startswith("="):
        raise ValueError(f"유효하지 않은 Excel 수식 형식입니다: {value}. " "Excel 수식은 '=' 문자로 시작해야 합니다.")

    # 괄호 짝 검사
    if value.count("(") != value.count(")"):
        raise ValueError(f"유효하지 않은 Excel 수식 형식입니다: {value}. " "괄호의 짝이 맞지 않습니다.")

    # 기본적인 Excel 함수 패턴
    # 예: =SUM(...), =AVERAGE(...), =COUNT(...) 등
    # 중첩된 괄호를 최대 3단계까지 허용
    function_pattern = r"=[A-Z]+\([^()]*(?:\([^()]*(?:\([^()]*\)[^()]*)*\)[^()]*)*\)"

    # 셀 참조 패턴 (시트 이름 포함 가능)
    # 예: =A1, =Sheet1!A1, ='My Sheet'!A1
    cell_ref_pattern = r"=(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?\$?[A-Z]{1,3}\$?[1-9][0-9]*"

    # 수식 연산 패턴 (비교 연산자 추가)
    # 예: =A1+B1, =C1*D1, =A1>0, =B1>=100
    operation_pattern = r"=.*(?:[\+\-\*/\<\>\=]|>=|<=).*"

    # 문자열 리터럴 패턴
    # 예: ="Hello", =CONCATENATE("Hello", A1)
    string_pattern = r'="[^"]*"'

    # 숫자 리터럴 패턴
    # 예: =123, =1.23, =-45.67
    number_pattern = r"=\-?\d+(\.\d+)?"

    patterns = [function_pattern, cell_ref_pattern, operation_pattern, string_pattern, number_pattern]

    # 최소한 하나의 패턴과 일치해야 함
    if not any(re.match(pattern, value) for pattern in patterns):
        raise ValueError(
            f"유효하지 않은 Excel 수식 형식입니다: {value}. "
            "지원되는 수식 패턴과 일치하지 않습니다.\n"
            "예시:\n"
            '- 기본 수식: =A1, =123, ="text"\n'
            "- 수식 연산: =A1+B1, =C1*D1\n"
            "- 함수 호출: =SUM(A1:A10)\n"
            "- 시트 참조: =Sheet1!A1, ='My Sheet'!B2"
        )

    return value

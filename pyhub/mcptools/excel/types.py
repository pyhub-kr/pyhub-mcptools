import re
from typing import Annotated, Optional

from pydantic import BeforeValidator, Field


def validate_excel_range(value: Optional[str]) -> Optional[str]:
    """Excel 범위 형식을 검증하는 함수 (시트 이름, 절대/상대 참조 포함)"""
    if value is None:
        return None

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


# Pydantic과 호환되는 타입 어노테이션 정의
ExcelRange = Annotated[
    str,
    BeforeValidator(validate_excel_range),
    Field(description="Excel Range (ex: 'A1', 'A1:C3', 'Sheet1!A1', '$A$1:$C$3')"),
]

"""데이터 변환 유틸리티"""

import json
from typing import Any, List, Optional, Tuple, Union


def ensure_2d_array(values: Union[List[Any], List[List[Any]]]) -> List[List[Any]]:
    """1차원 또는 2차원 배열을 항상 2차원 배열로 변환"""
    if not values:
        return [[]]

    # 이미 2차원 배열인 경우
    if isinstance(values[0], list):
        return values

    # 1차원 배열인 경우 2차원으로 변환
    return [values]


def excel_range_to_a1(sheet_name: str, start_col: int, start_row: int,
                      end_col: Optional[int] = None, end_row: Optional[int] = None) -> str:
    """Excel 스타일 범위를 A1 표기법으로 변환

    Args:
        sheet_name: 시트 이름
        start_col: 시작 열 (1부터 시작)
        start_row: 시작 행 (1부터 시작)
        end_col: 끝 열 (선택사항)
        end_row: 끝 행 (선택사항)

    Returns:
        A1 표기법 문자열 (예: "Sheet1!A1:B10")
    """
    def col_to_letter(col_num: int) -> str:
        """숫자를 열 문자로 변환 (1 -> A, 26 -> Z, 27 -> AA)"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(ord('A') + col_num % 26) + result
            col_num //= 26
        return result

    start = f"{col_to_letter(start_col)}{start_row}"

    if end_col and end_row:
        end = f"{col_to_letter(end_col)}{end_row}"
        return f"{sheet_name}!{start}:{end}"
    else:
        return f"{sheet_name}!{start}"


def parse_sheet_range(sheet_range: str) -> Tuple[str, Optional[str]]:
    """시트 범위 문자열을 시트명과 범위로 분리

    Args:
        sheet_range: "Sheet1!A1:B10" 형식의 문자열

    Returns:
        (시트명, 범위) 튜플
    """
    if "!" in sheet_range:
        sheet_name, range_str = sheet_range.split("!", 1)
        return sheet_name, range_str
    else:
        # 시트명만 있는 경우
        return sheet_range, None


def json_dumps(obj: Any) -> str:
    """JSON 직렬화 (한글 유니코드 이스케이프 방지)"""
    return json.dumps(obj, ensure_ascii=False, indent=2)
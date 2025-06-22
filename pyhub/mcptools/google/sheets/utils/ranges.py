"""범위 처리 유틸리티"""

import re
from typing import Dict, Optional, Tuple


def parse_a1_notation(a1: str) -> Tuple[int, int]:
    """A1 표기법을 (행, 열) 튜플로 변환

    Args:
        a1: "A1", "B10" 등의 A1 표기법

    Returns:
        (행 번호, 열 번호) - 1부터 시작
    """
    match = re.match(r'^([A-Z]+)(\d+)$', a1.upper())
    if not match:
        raise ValueError(f"Invalid A1 notation: {a1}")

    col_str, row_str = match.groups()

    # 열 문자를 숫자로 변환
    col = 0
    for char in col_str:
        col = col * 26 + (ord(char) - ord('A') + 1)

    row = int(row_str)

    return row, col


def expand_range(range_str: str) -> Tuple[int, int, int, int]:
    """A1:B10 형식의 범위를 (시작행, 시작열, 끝행, 끝열)로 확장

    Args:
        range_str: "A1:B10" 형식의 범위

    Returns:
        (start_row, start_col, end_row, end_col) - 1부터 시작
    """
    if ':' in range_str:
        start, end = range_str.split(':', 1)
        start_row, start_col = parse_a1_notation(start)
        end_row, end_col = parse_a1_notation(end)
    else:
        # 단일 셀
        row, col = parse_a1_notation(range_str)
        start_row = end_row = row
        start_col = end_col = col

    return start_row, start_col, end_row, end_col


def get_range_info(range_str: str) -> Dict[str, int]:
    """범위 정보를 딕셔너리로 반환

    Args:
        range_str: "A1:B10" 형식의 범위

    Returns:
        {
            "startRow": 1,
            "startColumn": 1,
            "endRow": 10,
            "endColumn": 2,
            "rowCount": 10,
            "columnCount": 2
        }
    """
    start_row, start_col, end_row, end_col = expand_range(range_str)

    return {
        "startRow": start_row,
        "startColumn": start_col,
        "endRow": end_row,
        "endColumn": end_col,
        "rowCount": end_row - start_row + 1,
        "columnCount": end_col - start_col + 1,
    }
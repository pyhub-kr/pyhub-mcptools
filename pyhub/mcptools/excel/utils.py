import asyncio
import csv
import json
import re
import subprocess
import unicodedata
from ast import literal_eval
from io import StringIO
from typing import Any, Optional, Union

import xlwings as xw
from django.template import Context, Template

from pyhub.mcptools.excel.types import ExcelExpandMode


def get_sheet(
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> xw.Sheet:
    if book_name is None:
        book = xw.books.active
    else:
        book = xw.books[book_name]

    if sheet_name is None:
        sheet = book.sheets.active
    else:
        sheet = book.sheets[sheet_name]

    return sheet


def get_range(
    sheet_range: str,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    expand_mode: Optional[ExcelExpandMode] = None,
) -> xw.Range:
    # sheet_range가 "Sheet1!A1" 형태일 경우 분리
    if sheet_range and "!" in sheet_range:
        parsed_sheet_name, sheet_range = sheet_range.split("!", 1)
        sheet_name = sheet_name or parsed_sheet_name

    # expand_mode가 지정되어있을 때, 시트 범위에서 시작 셀 좌표만 추출.
    # Claude에서 expand_mode를 지정했을 때에도 sheet range를 너무 크게 잡을 때가 있음.
    if expand_mode is not None:
        sheet_range = sheet_range.split(":", 1)[0]

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    if sheet_range is None:
        range_ = sheet.used_range
    else:
        range_ = sheet.range(sheet_range)

    if expand_mode is not None:
        range_ = range_.expand(mode=expand_mode.value.lower())

    return range_


def fix_data(sheet_range: str, values: Union[str, list]) -> Union[str, list]:
    """
    sheet_range가 열 방향인데, 값이 리스트이지만 중첩 리스트가 아니라면 중첩 리스트로 변환합니다.

    Args:
        sheet_range: Excel 범위 문자열 (예: "A1:A10", "B1", "Sheet1!C1:C5")
        values: 셀에 입력할 값들

    Returns:
        변환된 값 또는 원본 값
    """

    if (
        isinstance(values, str)
        or not isinstance(values, list)
        or (isinstance(values, list) and values and isinstance(values[0], list))
    ):
        return values

    # range가 범위를 포함하는지 확인
    range_pattern = (
        r"(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?"
    )
    match = re.match(range_pattern, sheet_range)

    if not match:
        return values

    # 단일 셀 또는 범위의 시작과 끝을 추출
    start_cell = match.group(1)
    end_cell = match.group(2)

    # 단일 셀인 경우 (범위가 없는 경우)
    if not end_cell:
        # 단일 셀에 중첩되지 않은 리스트가 입력된 경우 가공하지 않음
        return values

    # 열 방향 범위인지 확인 (예: A1:A10)
    start_col = re.search(r"[A-Z]+", start_cell).group(0)
    end_col = re.search(r"[A-Z]+", end_cell).group(0)

    start_row = re.search(r"[0-9]+", start_cell).group(0)
    end_row = re.search(r"[0-9]+", end_cell).group(0)

    # 열이 같고 행이 다르면 열 방향 범위
    if start_col == end_col and start_row != end_row:
        # 평면 리스트를 중첩 리스트로 변환
        return [[value] for value in values]

    return values


def json_loads(json_str: str) -> Union[dict, str]:
    if isinstance(json_str, (str, bytes)):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                return literal_eval(json_str)
            except (ValueError, SyntaxError):
                pass

    return json_str


def json_dumps(json_data: Union[list, dict]) -> str:
    return json.dumps(json_data, ensure_ascii=False)


def convert_to_csv(data: list[list[Any]]) -> str:
    """Convert 2D data to CSV string format.

    Args:
        data: 2D list of data from Excel

    Returns:
        String in CSV format
    """
    if not data:
        return ""

    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(data)
    return output.getvalue()


def normalize_text(text: str) -> str:
    """Normalize Unicode text to NFC form for consistent handling of Korean characters."""
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


async def applescript_run(
    script: Union[str, Template],
    context: Optional[dict] = None,
) -> str:
    if context is None:
        context = {}

    if isinstance(script, Template):
        rendered_script = script.render(Context(context))
    else:
        rendered_script = script.format(**context)

    process = await asyncio.create_subprocess_exec(
        "osascript",
        "-e",
        rendered_script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    stdout = stdout_bytes.decode().strip()
    stderr = stderr_bytes.decode().strip()

    if process.returncode != 0:
        raise RuntimeError(stderr)

    return stdout


def applescript_run_sync(
    script: Union[str, Template],
    context: Optional[dict] = None,
) -> str:
    if context is None:
        context = {}

    if isinstance(script, Template):
        rendered_script = script.render(Context(context))
    else:
        rendered_script = script.format(**context)

    process = subprocess.run(
        ["osascript", "-e", rendered_script],
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip())

    return process.stdout.strip()


def csv_loads(csv_str: str) -> list[list[str]]:
    """Convert a CSV string to a list of lists.
    각 행의 열 개수가 다른 경우, 부족한 열은 빈 문자열로 채워서 반환합니다.

    Args:
        csv_str: CSV formatted string with newlines and commas

    Returns:
        List of lists containing the CSV data, with rows padded to equal length

    Examples:
        >>> csv_loads("a,b,c\\n1,2,3")
        [['a', 'b', 'c'], ['1', '2', '3']]
        >>> csv_loads("a,b,c\\n1,2\\nx")
        [['a', 'b', 'c'], ['1', '2', ''], ['x', '', '']]
    """
    if not csv_str.strip():
        return [[""]]

    # 리터럴 \\n을 실제 개행 문자로 변환
    csv_str = csv_str.replace("\\n", "\n")

    f = StringIO(csv_str)
    reader = csv.reader(f, dialect="excel")
    data = [row for row in reader]

    # 각 행의 열 개수를 동일하게 맞춥니다
    return normalize_2d_data(data)


def normalize_2d_data(data: list[list[Any]]) -> list[list[Any]]:
    """2차원 데이터의 각 행의 열 개수를 동일하게 맞춥니다.
    부족한 열은 빈 문자열로 채웁니다.
    입력값이 2차원 리스트가 아닌 경우 그대로 반환합니다.

    Args:
        data: 2차원 리스트 데이터

    Returns:
        정규화된 2차원 리스트 또는 원본 데이터

    Examples:
        >>> data = [['a', 'b', 'c'], ['1', '2'], ['x']]
        >>> normalize_2d_data(data)
        [['a', 'b', 'c'], ['1', '2', ''], ['x', '', '']]
        >>> normalize_2d_data(['a', 'b', 'c'])
        ['a', 'b', 'c']
        >>> normalize_2d_data("hello")
        "hello"
    """
    # 입력값이 리스트가 아니거나, 빈 리스트이면 그대로 반환
    if not isinstance(data, list) or not data:
        return data

    # 입력값이 2차원 리스트가 아니면 그대로 반환
    if not all(isinstance(row, list) for row in data):
        return data

    # 가장 긴 행의 길이를 찾습니다
    max_length = max(len(row) for row in data)

    # 각 행을 순회하면서 부족한 열을 빈 문자열로 채웁니다
    return [row + [""] * (max_length - len(row)) for row in data]

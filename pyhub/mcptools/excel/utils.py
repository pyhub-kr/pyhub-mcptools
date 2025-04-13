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

from pyhub.mcptools.excel.types import ExcelRange


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
    sheet_range: ExcelRange,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> xw.Range:
    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    if sheet_range is None:
        range_ = sheet.used_range
    else:
        range_ = sheet.range(sheet_range)

    return range_


def fix_data(sheet_range: ExcelRange, values: Union[str, list]) -> Union[str, list]:
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

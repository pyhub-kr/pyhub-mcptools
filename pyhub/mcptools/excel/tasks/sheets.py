import xlwings as xw
from pydantic import Field

from pyhub.mcptools.core.q2 import q_task, TaskGroup
from pyhub.mcptools.excel.decorators import macos_excel_request_permission
from pyhub.mcptools.excel.utils import normalize_text, get_sheet, json_dumps


@q_task(group=TaskGroup.XLWINGS)
@macos_excel_request_permission
def get_opened_workbooks() -> str:
    """Get a list of all open workbooks and their sheets in Excel

    Returns:
        str: JSON string containing:
            - books: List of open workbooks
                - name: Workbook name
                - fullname: Full path of workbook
                - sheets: List of sheets in workbook
                    - name: Sheet name
                    - index: Sheet index
                    - range: Used range address (e.g. "$A$1:$E$665")
                    - count: Total number of cells in used range
                    - shape: Tuple of (rows, columns) in used range
                    - active: Whether this is the active sheet
                - active: Whether this is the active workbook
    """

    return json_dumps(
        {
            "books": [
                {
                    "name": normalize_text(book.name),
                    "fullname": normalize_text(book.fullname),
                    "sheets": [
                        {
                            "name": normalize_text(sheet.name),
                            "index": sheet.index,
                            "range": sheet.used_range.get_address(),  # "$A$1:$E$665"
                            "count": sheet.used_range.count,  # 3325 (total number of cells)
                            "shape": sheet.used_range.shape,  # (655, 5)
                            "active": sheet == xw.sheets.active,
                            "table_names": [table.name for table in sheet.tables],
                        }
                        for sheet in book.sheets
                    ],
                    "active": book == xw.books.active,
                }
                for book in xw.books
            ]
        }
    )


@q_task(group=TaskGroup.XLWINGS)
@macos_excel_request_permission
def find_data_ranges(
    book_name: str = Field(
        default="",
        description="Name of workbook to use. Optional.",
        examples=["Sales.xlsx", "Report2023.xlsx"],
    ),
    sheet_name: str = Field(
        default="",
        description="Name of sheet to use. Optional.",
        examples=["Sheet1", "Sales2023"],
    ),
) -> str:
    """Detects and returns all distinct data block ranges in an Excel worksheet.

    Scans worksheet to find contiguous blocks of non-empty cells.
    Uses active workbook/sheet if not specified.

    Detection Rules:
        - Finds contiguous non-empty cell blocks
        - Uses Excel's table expansion
        - Empty cells act as block boundaries
        - Merges overlapping/adjacent blocks

    Returns:
        str: JSON list of range addresses (e.g., ["A1:I11", "K1:P11"])
    """

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

    data_ranges = []
    visited = set()

    used = sheet.used_range
    start_row = used.row
    start_col = used.column
    n_rows = used.rows.count
    n_cols = used.columns.count

    # 전체 데이터를 메모리로 한 번에 가져옴 (2D 리스트)
    data_grid = used.value

    # 엑셀 한 셀일 경우, data_grid 값은 단일 값이므로 보정
    if not isinstance(data_grid, list):
        data_grid = [[data_grid]]
    elif isinstance(data_grid[0], (str, int, float, type(None))):
        data_grid = [data_grid]

    for r in range(n_rows):
        for c in range(n_cols):
            abs_row = start_row + r
            abs_col = start_col + c
            addr = (abs_row, abs_col)

            if addr in visited:
                continue

            # 데이터 시작 부분에 대해서 범위 좌표 계산
            val = data_grid[r][c]
            if val is not None and str(val).strip() != "":
                cell = sheet.range((abs_row, abs_col))
                block = cell.expand("table")

                top = block.row
                left = block.column
                bottom = top + block.rows.count - 1
                right = left + block.columns.count - 1

                for rr in range(top, bottom + 1):
                    for cc in range(left, right + 1):
                        visited.add((rr, cc))

                data_ranges.append(block.address)

    return json_dumps(data_ranges)

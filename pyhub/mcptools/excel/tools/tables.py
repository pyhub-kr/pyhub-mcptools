from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.tasks import tables as tables_tasks


# TODO: macOS 지원 추가 : macOS에서 xlwings 활용 테이블 생성 시에 오류 발생


@mcp.tool(
    delegator=tables_tasks.convert_to_table,
    timeout=5,
    enabled=OS.current_is_windows(),
)
async def excel_convert_to_table():
    pass


# TODO: table 목록/내역 반환


@mcp.tool(delegator=tables_tasks.add_pivot_table, timeout=5)
async def excel_add_pivot_table():
    pass


@mcp.tool(delegator=tables_tasks.get_pivot_tables, timeout=5)
async def excel_get_pivot_tables():
    pass


@mcp.tool(delegator=tables_tasks.remove_pivot_tables, timeout=5)
async def excel_remove_pivot_tables():
    pass

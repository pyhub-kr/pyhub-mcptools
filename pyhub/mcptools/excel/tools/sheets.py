from pyhub.mcptools import mcp
from pyhub.mcptools.core.choices import OS
from pyhub.mcptools.excel.tasks import sheets as sheets_tasks


@mcp.tool(delegator=sheets_tasks.get_opened_workbooks, timeout=10)
async def excel_get_opened_workbooks():
    pass


@mcp.tool(delegator=sheets_tasks.find_data_ranges, timeout=5)
async def excel_find_data_ranges():
    pass


@mcp.tool(
    delegator=sheets_tasks.get_special_cells_address,
    timeout=5,
    enabled=OS.current_is_windows(),
)
async def excel_get_special_cells_address():
    pass


@mcp.tool(delegator=sheets_tasks.get_values, timeout=5)
async def excel_get_values():
    pass


@mcp.tool(delegator=sheets_tasks.set_values, timeout=5)
async def excel_set_values():
    pass


@mcp.tool(delegator=sheets_tasks.set_styles, timeout=30)
async def excel_set_styles():
    pass


@mcp.tool(delegator=sheets_tasks.autofit, timeout=5)
async def excel_autofit():
    pass


@mcp.tool(delegator=sheets_tasks.set_formula, timeout=5)
async def excel_set_formula():
    pass


@mcp.tool(delegator=sheets_tasks.add_sheet, timeout=5)
async def excel_add_sheet():
    pass

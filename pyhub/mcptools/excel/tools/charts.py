from pyhub.mcptools import mcp
from pyhub.mcptools.excel.tasks import charts as charts_tasks


@mcp.tool(delegator=charts_tasks.get_charts)
async def excel_get_charts():
    pass


@mcp.tool(delegator=charts_tasks.add_chart)
async def excel_add_chart():
    pass


@mcp.tool(delegator=charts_tasks.set_chart_props)
async def excel_set_chart_props():
    pass

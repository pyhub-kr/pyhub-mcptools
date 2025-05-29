"""Microsoft tools aggregator - re-exports tools from all Microsoft products."""

# Import Outlook tools
from pyhub.mcptools.microsoft.outlook.tools import (
    outlook,
)

# Import Excel tools
from pyhub.mcptools.microsoft.excel.tools import (
    # Sheets - Compatibility tools
    excel_get_opened_workbooks,
    excel_get_values,
    excel_set_values,
    # Sheets - Integrated tools
    excel_get_info,
    excel_set_cell_data,
    # Sheets - Independent tools
    excel_find_data_ranges,
    excel_set_styles,
    excel_autofit,
    excel_add_sheet,
    # Charts
    excel_get_charts,
    excel_add_chart,
    excel_set_chart_props,
    # Tables
    excel_convert_to_table,
    excel_add_pivot_table,
    excel_get_pivot_tables,
    excel_remove_pivot_tables,
)

# Future: Add other Microsoft product tools (Teams, OneDrive, etc.)

__all__ = [
    # Outlook tools
    "outlook",
    # Excel tools - Sheets (Compatibility)
    "excel_get_opened_workbooks",
    "excel_get_values",
    "excel_set_values",
    # Excel tools - Sheets (Integrated)
    "excel_get_info",
    "excel_set_cell_data",
    # Excel tools - Sheets (Independent)
    "excel_find_data_ranges",
    "excel_set_styles",
    "excel_autofit",
    "excel_add_sheet",
    # Excel tools - Charts
    "excel_get_charts",
    "excel_add_chart",
    "excel_set_chart_props",
    # Excel tools - Tables
    "excel_convert_to_table",
    "excel_add_pivot_table",
    "excel_get_pivot_tables",
    "excel_remove_pivot_tables",
    # Future: Teams tools
    # Future: OneDrive tools
]

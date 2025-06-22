"""Google MCP 도구 통합

모든 Google 서비스의 MCP 도구를 하나로 통합하여 제공합니다.
현재는 Google Sheets만 포함되어 있으며, 향후 다른 Google 서비스가 추가될 예정입니다.
"""

# Google Sheets 도구는 mcp.tool 데코레이터에 의해 자동 등록됨
from pyhub.mcptools.google.sheets.tools import sheets  # noqa
import os

import django
from django.conf import settings
from mcp.server.fastmcp import FastMCP

from ..core.utils import activate_timezone

mcp: FastMCP

if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyhub.mcp_tools.core.settings")
    django.setup()

    activate_timezone()

    mcp = FastMCP(
        name="pyhub-mcp-tools",
        # instructions=None,
        # ** settings,
    )


__all__ = ["mcp"]

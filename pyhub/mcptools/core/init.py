import os

import django
from django.conf import settings
from mcp.server.fastmcp import FastMCP

from pyhub.mcptools.core.utils import activate_timezone

mcp: FastMCP

if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyhub.mcptools.core.settings")
    django.setup()

    activate_timezone()

    mcp = FastMCP(
        name="pyhub-mcptools",
        # instructions=None,
        # ** settings,
    )


__all__ = ["mcp"]

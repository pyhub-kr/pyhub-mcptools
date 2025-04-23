import os

import django
from django.conf import settings

from pyhub.mcptools.core.fastmcp import FastMCP
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
        # debug=settings.DEBUG,
    )


__all__ = ["mcp"]

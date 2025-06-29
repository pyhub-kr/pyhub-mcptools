"""Entry point for Google MCP tools."""

import os

# Set required environment variables for Google Sheets
os.environ.setdefault("USE_GOOGLE_SHEETS", "1")

from pyhub.mcptools.core.cli import app

from . import cli_commands  # noqa
from .gmail.tools import labels, messages, search  # noqa

# Import to register tools and CLI commands
from .sheets.tools import sheets  # noqa

if __name__ == "__main__":
    app()

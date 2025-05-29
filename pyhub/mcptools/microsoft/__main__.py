"""Entry point for Microsoft MCP tools."""

from pyhub.mcptools.core.cli import app

# Import to register tools
from .outlook import tools  # noqa

if __name__ == "__main__":
    app()

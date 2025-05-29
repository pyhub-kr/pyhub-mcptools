"""Sentiment analysis MCP tools entry point."""

from pyhub.mcptools.core.cli import app
from pyhub.mcptools.sentiment import tools  # noqa

if __name__ == "__main__":
    app()

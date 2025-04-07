"""Pytest configuration file."""

import pytest


@pytest.fixture
async def mcp_client():
    """Return a FastMCP client instance for tests."""
    from pyhub.mcptools import mcp

    return mcp

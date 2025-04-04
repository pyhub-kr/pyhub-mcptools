"""Pytest configuration file."""

import pytest


@pytest.fixture
async def mcp_client():
    """Return a FastMCP client instance for tests."""
    from pyhub.mcp_tools import mcp

    return mcp

"""Pytest configuration file."""

import pytest
from django.utils.translation import activate, deactivate


@pytest.fixture(autouse=True)
def use_english_language():
    """Set English as the default language for all tests."""
    activate('en-US')
    yield
    deactivate()


@pytest.fixture
async def mcp_client():
    """Return a FastMCP client instance for tests."""
    from pyhub.mcptools import mcp

    return mcp

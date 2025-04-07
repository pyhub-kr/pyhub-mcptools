"""Tests for the core module."""

from django.apps import apps


def test_mcp_client_initialization(mcp_client):
    """Test that the MCPClient and Django app can be initialized."""
    # Test MCPClient initialization
    assert mcp_client is not None
    assert hasattr(mcp_client, "list_tools")

    app_configs = list(apps.get_app_configs())
    assert len(app_configs) > 0

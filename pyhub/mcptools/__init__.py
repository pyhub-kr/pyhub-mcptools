"""
PyHub MCP Tools
"""

__all__ = ["mcp"]

# Don't import anything at module level to avoid circular imports during Django setup
# The mcp instance will be available after Django setup completes


def __getattr__(name):
    if name == "mcp":
        # Import only when accessed
        from .core.init import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

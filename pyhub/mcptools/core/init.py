import os

# Placeholder for the MCP instance - will be initialized when needed
mcp = None
_initialized = False


def init_django_and_mcp():
    """Initialize Django and MCP instance."""
    global mcp, _initialized

    if _initialized:
        return mcp

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyhub.mcptools.core.settings")

    # Import Django components
    import django

    # Setup Django
    django.setup()

    # Now import MCP components after Django is ready
    from pyhub.mcptools.core.fastmcp import FastMCP
    from pyhub.mcptools.core.utils import activate_timezone

    activate_timezone()

    # Create MCP instance
    mcp = FastMCP(
        name="pyhub-mcptools",
        # instructions=None,
        # ** settings,
        # debug=settings.DEBUG,
    )

    _initialized = True
    return mcp


# Lazy wrapper that initializes on first access
class LazyMCP:
    def __getattr__(self, name):
        return getattr(init_django_and_mcp(), name)


# Export the lazy wrapper
mcp = LazyMCP()


__all__ = ["mcp"]

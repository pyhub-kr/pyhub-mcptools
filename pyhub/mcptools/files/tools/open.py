"""Open files with OS default applications.

This tool allows opening files with their associated default applications.
For example, Excel files open in Excel, PDFs in PDF viewer, etc.
"""

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.files.core import open_file_with_default_app


def _get_enabled_file_tools():
    """Check if file tools are enabled."""
    return settings.FS_LOCAL_HOME is not None


@mcp.tool(enabled=lambda: _get_enabled_file_tools())
async def file__open(
    path: str = Field(
        description="Path to the file to open",
        examples=["report.xlsx", "~/documents/presentation.pdf", "image.png"],
    ),
    wait: bool = Field(default=False, description="Wait for the application to close before returning"),
) -> str:
    """Open a file with the operating system's default application.

    Opens the file using the default application associated with the file type.
    For example, .xlsx files will open in Excel, .pdf in PDF viewer, etc.
    Use this when you need to open files for user viewing or editing in their native applications.

    Returns:
        Success message indicating the file was opened

    Raises:
        ValueError: If path is invalid or file cannot be opened
    """
    return await open_file_with_default_app(path, wait)

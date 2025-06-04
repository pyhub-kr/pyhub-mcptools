from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.fs import core
from pyhub.mcptools.fs.utils import EditOperation


def _get_enabled_fs_tools():
    """Lazy evaluation of FS tools enablement."""
    return settings.FS_LOCAL_HOME is not None


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__read_file(
    path: str = Field(
        description="Path to the file to read",
        examples=["data.txt", "~/documents/notes.md"],
    ),
) -> str:
    """Read the complete contents of a file from the file system.

    Args:
        path: Path to the file to read

    Returns:
        str: The contents of the file

    Raises:
        ValueError: If path is outside allowed directories or file cannot be read
    """

    return await core.read_file(path)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__read_multiple_files(
    paths: list[str] = Field(
        description="List of file paths to read",
        examples=[
            ["data1.txt", "data2.txt"],
            ["~/documents/notes.md", "./config.json"],
        ],
    ),
) -> str:
    """Read the contents of multiple files simultaneously.

    Args:
        paths: List of file paths to read

    Returns:
        str: Contents of all files, with file paths as headers and base64 encoded content

    Example output:
        data1.txt: SGVsbG8gV29ybGQ=
        data2.txt: eyJrZXkiOiAidmFsdWUifQ==
        data3.txt: Error - File not found
    """

    file_data = await core.read_multiple_files(paths)

    # Format results for backward compatibility
    results = []
    for data in file_data:
        if "error" in data:
            results.append(f"{data['path']}: Error - {data['error']}")
        else:
            results.append(f"{data['path']}: {data['content']}")

    return "\n".join(results)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__write_file(
    path: str = Field(
        description="Path where to write the file",
        examples=["output.txt", "~/documents/notes.md"],
    ),
    text_content: str = Field(
        "",
        description=(
            "Text Content to write to the file. If both text_content and base64_content are provided, "
            "text_content takes precedence."
        ),
        examples=["Hello World", "{'key': 'value'}"],
    ),
    base64_content: str = Field(
        "",
        description=(
            "Base64 encoded binary content to write to the file. "
            "This is used only when text_content is empty. The content will be decoded from base64 before writing."
        ),
        examples=["SGVsbG8gV29ybGQ=", "eydrZXknOiAndmFsdWUnfQ=="],
    ),
    text_encoding: str = Field("utf-8", description="Encoding of text_content"),
) -> str:
    """Create a new file or completely overwrite an existing file with new content.

    Returns:
        str: Success message indicating the file was written

    Raises:
        ValueError: If path is outside allowed directories or if write operation fails
    """

    if text_content:
        return await core.write_file(path, text_content, encoding=text_encoding)
    elif base64_content:
        return await core.write_file_base64(path, base64_content)
    else:
        raise ValueError("No content to write")


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__edit_file(
    path: str = Field(
        description="Path to the file to edit",
        examples=["script.py", "~/documents/notes.md"],
    ),
    edits: list[dict[str, str]] = Field(
        description="List of edit operations. Each edit should have 'old_text' and 'new_text'",
        examples=[
            [
                {"old_text": "def old_name", "new_text": "def new_name"},
                {"old_text": "print('hello')", "new_text": "print('world')"},
            ]
        ],
    ),
    dry_run: bool = Field(
        default=False,
        description="Preview changes using git-style diff format without applying them",
    ),
) -> str:
    """
    Make line-based edits to a text file.

    Args:
        path: Path to the file to edit
        edits: List of edit operations
        dry_run: If True, only show changes without applying them. Note that regardless of
                the dry_run value, this function always returns a git-style diff showing
                the changes.

    Returns:
        str: Git-style diff showing the changes. The same diff format is returned whether
             dry_run is True or False. The only difference is whether the changes are
             actually applied to the file.

    Raises:
        ValueError: If path is outside allowed directories or if edits cannot be applied
    """

    # Convert dict edits to EditOperation objects
    edit_operations = [EditOperation(old_text=edit["old_text"], new_text=edit["new_text"]) for edit in edits]

    return await core.edit_file(path, edit_operations, dry_run)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__create_directory(
    path: str = Field(
        description="Path of the directory to create",
        examples=["new_folder", "~/documents/project/src"],
    ),
) -> str:
    """Create a new directory or ensure a directory exists.

    Args:
        path: Path of the directory to create

    Returns:
        str: Success message indicating the directory was created

    Raises:
        ValueError: If path is outside allowed directories or if directory cannot be created
    """

    return await core.create_directory(path)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__list_directory(
    path: str = Field(
        description="Path of the directory to list",
        examples=[".", "~/documents", "project/src"],
    ),
    recursive: bool = Field(
        default=False,
        description="Whether to recursively list subdirectories",
    ),
    max_depth: int = Field(
        default=0,
        description="Maximum depth for recursive listing (0 for unlimited)",
    ),
) -> str:
    """Get a detailed listing of files and directories in a specified path.

    Args:
        path: Path of the directory to list
        recursive: If True, recursively list subdirectories
        max_depth: Maximum depth for recursive listing

    Returns:
        str: Formatted string containing directory listing:

    Raises:
        ValueError: If path is outside allowed directories or if directory cannot be read
    """

    listing = await core.list_directory(path, recursive, max_depth)

    # Format results for backward compatibility
    entries = []
    for item in listing:
        prefix = "[DIR]" if item["type"] == "directory" else "[FILE]"
        entries.append(f"{prefix} {item['path']}")

    return "\n".join(entries)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__move_file(
    source: str = Field(
        description="Source path of file or directory to move",
        examples=["old_name.txt", "~/documents/old_folder"],
    ),
    destination: str = Field(
        description="Destination path where to move the file or directory",
        examples=["new_name.txt", "~/documents/new_folder"],
    ),
) -> str:
    """
    Move or rename files and directories.

    Can move files between directories and rename them in a single operation.
    If the destination exists, the operation will fail.
    Works across different directories and can be used for simple renaming within the same directory.
    Both source and destination must be within allowed directories.

    Args:
        source: Source path of file or directory to move
        destination: Destination path where to move the file or directory

    Returns:
        str: Success message indicating the move operation was completed

    Raises:
        ValueError: If paths are outside allowed directories or if move operation fails
    """

    return await core.move_file(source, destination)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__find_files(
    path: str = Field(
        description="Base directory path to start search from",
        examples=[".", "~/documents", "project/src"],
    ),
    name_pattern: str = Field(
        default="",
        description="Pattern to match filenames (supports wildcards like *.py)",
        examples=["*.py", "test*", "*.{jpg,png}"],
    ),
    exclude_patterns: str = Field(
        default="",
        description="Patterns to exclude from search (e.g., ['*.pyc', '.git/**'])",
        examples=[["*.pyc", ".git/**"], ["node_modules/**", "*.tmp"]],
    ),
    max_depth: int = Field(
        default=0,
        description="Maximum depth to traverse (0 for unlimited)",
        examples=[1, 2, 3],
    ),
) -> str:
    """Recursively search for files using Linux find-like syntax.

    Returns:
        str: Newline-separated list of matching paths, or "No matches found" if none

    Raises:
        ValueError: If path is outside allowed directories or if search fails
    """

    # Parse exclude patterns from string
    exclude_list = [s.strip() for s in exclude_patterns.split(",") if s.strip()] if exclude_patterns else []

    results = await core.find_files(path, name_pattern, exclude_list, max_depth)

    if not results:
        return "No matches found"

    return "\n".join(results)


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__get_file_info(
    path: str = Field(
        description="Path to the file or directory to get info about",
        examples=["script.py", "~/documents/project"],
    ),
) -> str:
    """Retrieve detailed metadata about a file or directory.

    Args:
        path: Path to the file or directory to get info about

    Returns:
        str: Formatted string containing file/directory metadata

    Example output:
        size: 1234 bytes
        created: 2024-03-20 01:30:45 UTC
        modified: 2024-03-21 06:20:10 UTC
        accessed: 2024-03-21 06:20:10 UTC
        type: file
        permissions: 644

    Raises:
        ValueError: If path is outside allowed directories or if info cannot be retrieved
    """

    info = await core.get_file_info(path)

    # Format results for backward compatibility
    formatted_info = {
        "size": f"{info['size']:,} bytes",
        "created": info["created"].strftime("%Y-%m-%d %H:%M:%S UTC"),
        "modified": info["modified"].strftime("%Y-%m-%d %H:%M:%S UTC"),
        "accessed": info["accessed"].strftime("%Y-%m-%d %H:%M:%S UTC"),
        "type": info["type"],
        "permissions": info["permissions"],
    }

    return "\n".join(f"{key}: {value}" for key, value in formatted_info.items())


@mcp.tool(enabled=lambda: _get_enabled_fs_tools())
async def fs__list_allowed_directories() -> str:
    """
    Returns the list of directories that this server is allowed to access.

    Returns:
        str: Formatted string listing all allowed directories
    """

    return "Allowed directories:\n" + "\n".join(map(str, settings.FS_LOCAL_ALLOWED_DIRECTORIES))

import asyncio
import base64
import os
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

import aiofiles
from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.fs.utils import EditOperation, apply_file_edits, validate_path

ENABLED_FS_TOOLS = settings.FS_LOCAL_HOME is not None


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    try:
        async with aiofiles.open(valid_path, "r", encoding="utf-8") as f:
            return await f.read()
    except UnicodeDecodeError as e:
        raise ValueError(f"File {path} is not a valid text file") from e
    except IOError as e:
        raise ValueError(f"Error reading file {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    results = []
    for file_path in paths:
        try:
            valid_path = validate_path(file_path)
            async with aiofiles.open(valid_path, "rb") as f:  # 바이너리 모드로 읽기
                content = base64.b64encode(await f.read()).decode("utf-8")
            results.append(f"{file_path}: {content}")
        except (ValueError, IOError) as e:
            results.append(f"{file_path}: Error - {str(e)}")

    return "\n".join(results)


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    parent_dir = valid_path.parent
    if parent_dir.exists() is False:
        parent_dir.mkdir(parents=True, exist_ok=True)

    try:
        if text_content:
            async with aiofiles.open(valid_path, "wt", encoding=text_encoding) as f:
                await f.write(text_content)
        elif base64_content:
            try:
                binary_content = base64.b64decode(base64_content)
                async with aiofiles.open(valid_path, "wb") as f:
                    await f.write(binary_content)
            except Exception as e:
                raise ValueError(f"Invalid base64 content: {str(e)}") from e
        else:
            raise ValueError("No content to write")

        return f"Successfully wrote to {valid_path}"
    except IOError as e:
        raise ValueError(f"Error writing to file {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    # Convert dict edits to EditOperation objects
    edit_operations = [EditOperation(old_text=edit["old_text"], new_text=edit["new_text"]) for edit in edits]

    return await apply_file_edits(valid_path, edit_operations, dry_run)


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    try:
        valid_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory {path}"
    except IOError as e:
        raise ValueError(f"Error creating directory {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    try:
        if not recursive:
            # 기존의 단순 리스팅 로직
            entries: list[str] = []
            for entry in valid_path.iterdir():
                prefix = "[DIR]" if entry.is_dir() else "[FILE]"
                entries.append(f"{prefix} {entry.name}")
            return "\n".join(sorted(entries))

        # 재귀적 flat 리스트 포맷
        entries = []
        for entry in valid_path.rglob("*"):
            try:
                # max_depth 체크
                if max_depth > 0:
                    relative_path = entry.relative_to(valid_path)
                    if len(relative_path.parts) > max_depth:
                        continue

                prefix = "[DIR]" if entry.is_dir() else "[FILE]"
                relative_path = entry.relative_to(valid_path)
                entries.append(f"{prefix} {relative_path}")
            except ValueError:
                continue

        return "\n".join(sorted(entries))

    except IOError as e:
        raise ValueError(f"Error listing directory {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_source = validate_path(source)
    valid_dest = validate_path(destination)

    try:
        # Check if source exists and is a file
        if not valid_source.exists():
            raise ValueError(f"Source does not exist: {source}")
        if not valid_source.is_file():
            raise ValueError(f"Source must be a file: {source}")

        # If destination is a directory, use source filename
        if valid_dest.exists() and valid_dest.is_dir():
            valid_dest = valid_dest / valid_source.name
        elif valid_dest.exists():
            raise ValueError(f"Destination already exists: {valid_dest}")

        # Create parent directory of destination if it doesn't exist
        if valid_dest.parent:  # Skip if path is in current directory
            valid_dest.parent.mkdir(parents=True, exist_ok=True)

        valid_source.rename(valid_dest)
        return f"Successfully moved {source} to {valid_dest}"
    except IOError as e:
        raise ValueError(f"Error moving {source} to {valid_dest}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)
    exclude_patterns: list[str] = list(map(lambda s: s.strip(), exclude_patterns.split(",")))
    results = []

    try:
        # os.walk를 asyncio.to_thread로 감싸서 비동기로 처리
        for root, _, files in await asyncio.to_thread(os.walk, valid_path):
            root_path = Path(root)
            try:
                relative_root = root_path.relative_to(valid_path)
                current_depth = len(relative_root.parts)

                if max_depth > 0 and current_depth > max_depth:
                    continue

                for file in files:
                    file_path = root_path / file
                    try:
                        validate_path(file_path)
                        relative_path = file_path.relative_to(valid_path)

                        should_exclude = any(
                            fnmatch(str(relative_path), exclude_pattern) for exclude_pattern in exclude_patterns
                        )
                        if should_exclude:
                            continue

                        if name_pattern and not fnmatch(file, name_pattern):
                            continue

                        results.append(str(file_path))
                    except ValueError:
                        continue

            except ValueError:
                continue

        if not results:
            return "No matches found"

        return "\n".join(sorted(results))

    except IOError as e:
        raise ValueError(f"Error searching in {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
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

    valid_path = validate_path(path)

    try:
        # os.stat을 asyncio.to_thread로 감싸서 비동기로 처리
        stats = await asyncio.to_thread(os.stat, valid_path)

        created = datetime.fromtimestamp(stats.st_ctime, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        modified = datetime.fromtimestamp(stats.st_mtime, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        accessed = datetime.fromtimestamp(stats.st_atime, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        type_ = "directory" if valid_path.is_dir() else "file"
        permissions = oct(stats.st_mode)[-3:]

        info = {
            "size": f"{stats.st_size:,} bytes",
            "created": created,
            "modified": modified,
            "accessed": accessed,
            "type": type_,
            "permissions": permissions,
        }

        return "\n".join(f"{key}: {value}" for key, value in info.items())

    except IOError as e:
        raise ValueError(f"Error getting info for {path}: {str(e)}") from e


@mcp.tool(enabled=ENABLED_FS_TOOLS)
async def fs__list_allowed_directories() -> str:
    """
    Returns the list of directories that this server is allowed to access.

    Returns:
        str: Formatted string listing all allowed directories
    """

    return "Allowed directories:\n" + "\n".join(map(str, settings.FS_LOCAL_ALLOWED_DIRECTORIES))

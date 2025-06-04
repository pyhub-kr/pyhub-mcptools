"""Core file system operations that can be shared between fs tools and other modules.

This module provides core file I/O functions that are used by both:
1. fs tools (which expose these as MCP tools)
2. Other modules like files/excel.py (which need file I/O without tool-to-tool calls)

All operations respect the security policies defined in fs.utils.
"""

import base64
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles

from pyhub.mcptools.fs.utils import EditOperation, apply_file_edits, validate_path


async def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the complete contents of a file from the file system.

    Args:
        path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        str: The contents of the file

    Raises:
        ValueError: If path is outside allowed directories or file cannot be read
    """
    valid_path = validate_path(path)

    try:
        async with aiofiles.open(valid_path, "r", encoding=encoding) as f:
            return await f.read()
    except UnicodeDecodeError as e:
        raise ValueError(f"File {path} is not a valid text file") from e
    except IOError as e:
        raise ValueError(f"Error reading file {path}: {str(e)}") from e


async def read_file_binary(path: str) -> bytes:
    """Read the complete binary contents of a file from the file system.

    Args:
        path: Path to the file to read

    Returns:
        bytes: The binary contents of the file

    Raises:
        ValueError: If path is outside allowed directories or file cannot be read
    """
    valid_path = validate_path(path)

    try:
        async with aiofiles.open(valid_path, "rb") as f:
            return await f.read()
    except IOError as e:
        raise ValueError(f"Error reading file {path}: {str(e)}") from e


async def read_multiple_files(paths: List[str]) -> List[Dict[str, Any]]:
    """Read the contents of multiple files simultaneously.

    Args:
        paths: List of file paths to read

    Returns:
        List of dictionaries containing:
        - path: The file path
        - content: Base64 encoded content (if successful)
        - error: Error message (if failed)
        - size: File size in bytes (if successful)
    """
    results = []
    for file_path in paths:
        try:
            content_bytes = await read_file_binary(file_path)
            content_base64 = base64.b64encode(content_bytes).decode("utf-8")
            results.append({"path": file_path, "content": content_base64, "size": len(content_bytes)})
        except (ValueError, IOError) as e:
            results.append({"path": file_path, "error": str(e)})

    return results


async def write_file(path: str, content: Union[str, bytes], encoding: str = "utf-8") -> str:
    """Create a new file or completely overwrite an existing file with new content.

    Args:
        path: Path where to write the file
        content: Content to write (str for text, bytes for binary)
        encoding: Text encoding (only used if content is str)

    Returns:
        str: Success message indicating the file was written

    Raises:
        ValueError: If path is outside allowed directories or if write operation fails
    """
    valid_path = validate_path(path)

    # Create parent directory if it doesn't exist
    parent_dir = valid_path.parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    try:
        if isinstance(content, str):
            async with aiofiles.open(valid_path, "w", encoding=encoding) as f:
                await f.write(content)
        else:
            async with aiofiles.open(valid_path, "wb") as f:
                await f.write(content)

        return f"Successfully wrote to {valid_path}"
    except IOError as e:
        raise ValueError(f"Error writing to file {path}: {str(e)}") from e


async def write_file_base64(path: str, content_base64: str) -> str:
    """Write base64 encoded content to a file.

    Args:
        path: Path where to write the file
        content_base64: Base64 encoded content

    Returns:
        str: Success message indicating the file was written

    Raises:
        ValueError: If path is outside allowed directories or if write operation fails
    """
    try:
        binary_content = base64.b64decode(content_base64)
        return await write_file(path, binary_content)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {str(e)}") from e


async def edit_file(path: str, edits: List[EditOperation], dry_run: bool = False) -> str:
    """Make line-based edits to a text file.

    Args:
        path: Path to the file to edit
        edits: List of edit operations
        dry_run: If True, only show changes without applying them

    Returns:
        str: Git-style diff showing the changes

    Raises:
        ValueError: If path is outside allowed directories or if edits cannot be applied
    """
    valid_path = validate_path(path)
    return await apply_file_edits(valid_path, edits, dry_run)


async def create_directory(path: str) -> str:
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


async def list_directory(path: str, recursive: bool = False, max_depth: int = 0) -> List[Dict[str, Any]]:
    """Get a detailed listing of files and directories in a specified path.

    Args:
        path: Path of the directory to list
        recursive: If True, recursively list subdirectories
        max_depth: Maximum depth for recursive listing (0 for unlimited)

    Returns:
        List of dictionaries containing:
        - name: File/directory name
        - path: Relative path from the listing directory
        - type: "file" or "directory"

    Raises:
        ValueError: If path is outside allowed directories or if directory cannot be read
    """
    valid_path = validate_path(path)
    entries = []

    try:
        if not recursive:
            # Simple listing
            for entry in valid_path.iterdir():
                entries.append(
                    {"name": entry.name, "path": entry.name, "type": "directory" if entry.is_dir() else "file"}
                )
        else:
            # Recursive listing
            for entry in valid_path.rglob("*"):
                try:
                    relative_path = entry.relative_to(valid_path)
                    # Check max_depth
                    if max_depth > 0 and len(relative_path.parts) > max_depth:
                        continue

                    entries.append(
                        {
                            "name": entry.name,
                            "path": str(relative_path),
                            "type": "directory" if entry.is_dir() else "file",
                        }
                    )
                except ValueError:
                    continue

        return sorted(entries, key=lambda x: x["path"])

    except IOError as e:
        raise ValueError(f"Error listing directory {path}: {str(e)}") from e


async def move_file(source: str, destination: str) -> str:
    """Move or rename files and directories.

    Args:
        source: Source path of file to move
        destination: Destination path where to move the file

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
        if valid_dest.parent:
            valid_dest.parent.mkdir(parents=True, exist_ok=True)

        valid_source.rename(valid_dest)
        return f"Successfully moved {source} to {valid_dest}"
    except IOError as e:
        raise ValueError(f"Error moving {source} to {valid_dest}: {str(e)}") from e


async def get_file_info(path: str) -> Dict[str, Any]:
    """Retrieve detailed metadata about a file or directory.

    Args:
        path: Path to the file or directory to get info about

    Returns:
        Dictionary containing file/directory metadata:
        - size: File size in bytes
        - created: Creation timestamp
        - modified: Modification timestamp
        - accessed: Access timestamp
        - type: "file" or "directory"
        - permissions: File permissions

    Raises:
        ValueError: If path is outside allowed directories or if info cannot be retrieved
    """
    valid_path = validate_path(path)

    try:
        import asyncio
        from datetime import UTC, datetime

        # Get file stats asynchronously
        stats = await asyncio.to_thread(os.stat, valid_path)

        return {
            "size": stats.st_size,
            "created": datetime.fromtimestamp(stats.st_ctime, UTC),
            "modified": datetime.fromtimestamp(stats.st_mtime, UTC),
            "accessed": datetime.fromtimestamp(stats.st_atime, UTC),
            "type": "directory" if valid_path.is_dir() else "file",
            "permissions": oct(stats.st_mode)[-3:],
        }

    except IOError as e:
        raise ValueError(f"Error getting info for {path}: {str(e)}") from e


async def find_files(
    path: str, name_pattern: str = "", exclude_patterns: Optional[List[str]] = None, max_depth: int = 0
) -> List[str]:
    """Recursively search for files matching patterns.

    Args:
        path: Base directory path to start search from
        name_pattern: Pattern to match filenames (supports wildcards like *.py)
        exclude_patterns: Patterns to exclude from search
        max_depth: Maximum depth to traverse (0 for unlimited)

    Returns:
        List of matching file paths

    Raises:
        ValueError: If path is outside allowed directories or if search fails
    """
    import asyncio
    from fnmatch import fnmatch

    valid_path = validate_path(path)
    exclude_patterns = exclude_patterns or []
    results = []

    try:
        # Use asyncio.to_thread for blocking I/O operation
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

                        # Check exclusions
                        should_exclude = any(fnmatch(str(relative_path), pattern) for pattern in exclude_patterns)
                        if should_exclude:
                            continue

                        # Check name pattern
                        if name_pattern and not fnmatch(file, name_pattern):
                            continue

                        results.append(str(file_path))
                    except ValueError:
                        continue

            except ValueError:
                continue

        return sorted(results)

    except IOError as e:
        raise ValueError(f"Error searching in {path}: {str(e)}") from e

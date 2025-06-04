"""Core functions for file operations.

This module contains core functions used by file tools.
"""

import asyncio
import platform
import subprocess
from pathlib import Path

from pyhub.mcptools.fs.utils import validate_path


async def open_file_with_default_app(path: str, wait: bool = False) -> str:
    """Open a file with the operating system's default application.

    Opens the file using the default application associated with the file type.
    For example, .xlsx files will open in Excel, .pdf in PDF viewer, etc.

    Args:
        path: Path to the file to open
        wait: Whether to wait for the application to close before returning

    Returns:
        Success message indicating the file was opened

    Raises:
        ValueError: If path is invalid or file cannot be opened
    """
    # Validate path for security
    valid_path = validate_path(path)

    # Check if file exists
    if not valid_path.exists():
        raise ValueError(f"File not found: {path}")

    if not valid_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        system = platform.system()

        if system == "Windows":
            await _open_file_windows(valid_path, wait)
        elif system == "Darwin":  # macOS
            await _open_file_macos(valid_path, wait)
        elif system == "Linux":
            await _open_file_linux(valid_path, wait)
        else:
            raise ValueError(f"Unsupported operating system: {system}")

        return f"Successfully opened file with default application: {path}"

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to open file: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error opening file: {str(e)}") from e


async def _open_file_windows(path: Path, wait: bool) -> None:
    """Open file on Windows."""
    if wait:
        # On Windows, we can't easily wait for the application to close
        # So we'll use subprocess instead
        await asyncio.to_thread(subprocess.run, ["cmd", "/c", "start", "/wait", "", str(path)], shell=True, check=True)
    else:
        # Use os.startfile on Windows (non-wait mode)
        try:
            import os

            # Check if startfile is available (Windows only)
            if not hasattr(os, "startfile"):
                raise AttributeError("os.startfile is only available on Windows")

            await asyncio.to_thread(os.startfile, str(path))
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot use Windows file opening on non-Windows system: {str(e)}") from e


async def _open_file_macos(path: Path, wait: bool) -> None:
    """Open file on macOS."""
    cmd = ["open"]
    if wait:
        cmd.append("-W")  # Wait for application to close
    cmd.append(str(path))

    await asyncio.to_thread(subprocess.run, cmd, check=True)


async def _open_file_linux(path: Path, wait: bool) -> None:
    """Open file on Linux."""
    cmd = ["xdg-open", str(path)]

    if wait:
        # xdg-open doesn't have a wait option, so we run it synchronously
        process = await asyncio.to_thread(subprocess.Popen, cmd)
        await asyncio.to_thread(process.wait)
    else:
        await asyncio.to_thread(subprocess.run, cmd, check=True)

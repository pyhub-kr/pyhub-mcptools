import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.conf import settings


def validate_path(requested_path: str) -> Path:
    """
    Validate and normalize a file path.

    Args:
        requested_path: The path to validate (str or Path)

    Returns:
        Path: The normalized absolute path if valid

    Raises:
        ValueError: If path is outside allowed directories or if relative path is provided without FS_LOCAL_HOME
    """

    path = Path(requested_path).expanduser()

    # 상대 경로인 경우 처리
    if not path.is_absolute():
        if settings.FS_LOCAL_HOME is None:
            raise ValueError("Cannot resolve relative path: FS_LOCAL_HOME is not set")
        path = Path(settings.FS_LOCAL_HOME) / path

    # Expand ~ to user's home directory if present
    allowed_local_directories = [Path(_path).resolve() for _path in settings.FS_LOCAL_ALLOWED_DIRECTORIES]

    if len(allowed_local_directories) == 0:
        raise ValueError("No allowed local directories are set")

    # Convert to absolute path and resolve any symlinks
    try:
        normalized_requested = path.resolve()

        # Check if path is within allowed directories
        is_allowed = any(
            str(normalized_requested).startswith(str(local_path)) for local_path in allowed_local_directories
        )
        if not is_allowed:
            raise ValueError(f"Access denied - path outside allowed directories: {normalized_requested}")
        return normalized_requested
    except FileNotFoundError as e:
        # For new files that don't exist yet, verify parent directory
        parent_dir = Path(requested_path).parent
        try:
            real_parent_path = parent_dir.resolve()
            is_parent_allowed = any(
                str(real_parent_path).startswith(str(Path(dir_).resolve())) for dir_ in allowed_local_directories
            )
            if not is_parent_allowed:
                raise ValueError("Access denied - parent directory outside allowed directories") from e
            return Path(requested_path)
        except FileNotFoundError as e:
            raise ValueError(f"Parent directory does not exist: {parent_dir}") from e


@dataclass
class EditOperation:
    """File edit operation."""

    old_text: str
    new_text: str


@dataclass
class TreeEntry:
    """Directory tree entry."""

    name: str
    type: str  # 'file' or 'directory'
    children: Optional[list["TreeEntry"]] = None


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to \n."""
    return text.replace("\r\n", "\n")


def create_unified_diff(original_content: str, new_content: str, filepath: Path) -> str:
    """
    Create a unified diff between original and new content.

    Args:
        original_content: Original file content
        new_content: Modified file content
        filepath: Name of the file for the diff header (str or Path)

    Returns:
        str: Unified diff format string
    """
    # Ensure consistent line endings
    original = normalize_line_endings(original_content)
    modified = normalize_line_endings(new_content)

    # Convert filepath to string if it's a Path object
    filepath_str = str(filepath)

    # Create diff
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=filepath_str,
        tofile=filepath_str,
        fromfiledate="original",
        tofiledate="modified",
    )

    return "".join(diff)


def apply_file_edits(
    file_path: Path,
    edits: list[EditOperation],
    dry_run: bool = False,
) -> str:
    """
    Apply edits to a file and return the diff.

    Args:
        file_path: Path to the file to edit
        edits: List of edit operations to apply
        dry_run: If True, only show changes without applying them

    Returns:
        str: Unified diff showing the changes

    Raises:
        ValueError: If edits cannot be applied
    """
    # Read and normalize file content

    with file_path.open("r", encoding="utf-8") as f:
        content = normalize_line_endings(f.read())

    # Apply edits sequentially
    modified_content = content
    for edit in edits:
        old_text = normalize_line_endings(edit.old_text)
        new_text = normalize_line_endings(edit.new_text)

        # Try exact match first
        if old_text in modified_content:
            modified_content = modified_content.replace(old_text, new_text)
            continue

        # Try line-by-line matching with whitespace flexibility
        old_lines = old_text.split("\n")
        content_lines = modified_content.split("\n")
        match_found = False

        for i in range(len(content_lines) - len(old_lines) + 1):
            potential_match = content_lines[i : i + len(old_lines)]

            # Compare lines with normalized whitespace
            is_match = all(
                old_line.strip() == content_line.strip()
                for old_line, content_line in zip(old_lines, potential_match, strict=False)
            )

            if is_match:
                # Preserve original indentation of first line
                original_indent = content_lines[i].replace(content_lines[i].lstrip(), "")
                new_lines = []

                for j, line in enumerate(new_text.split("\n")):
                    if j == 0:
                        # First line gets original indentation
                        new_lines.append(original_indent + line.lstrip())
                    else:
                        # Try to preserve relative indentation for other lines
                        old_indent = old_lines[j].replace(old_lines[j].lstrip(), "")
                        new_indent = line.replace(line.lstrip(), "")
                        if old_indent and new_indent:
                            relative_indent = len(new_indent) - len(old_indent)
                            new_lines.append(original_indent + " " * max(0, relative_indent) + line.lstrip())
                        else:
                            new_lines.append(line)

                content_lines[i : i + len(old_lines)] = new_lines
                modified_content = "\n".join(content_lines)
                match_found = True
                break

        if not match_found:
            raise ValueError(f"Could not find exact match for edit:\n{edit.old_text}")

    # Create unified diff
    diff = create_unified_diff(content, modified_content, file_path)

    # Format diff with appropriate number of backticks
    num_backticks = 3
    while "`" * num_backticks in diff:
        num_backticks += 1
    formatted_diff = f"{'`' * num_backticks}diff\n{diff}{'`' * num_backticks}\n\n"

    if not dry_run:
        with file_path.open("w", encoding="utf-8") as f:
            f.write(modified_content)

    return formatted_diff

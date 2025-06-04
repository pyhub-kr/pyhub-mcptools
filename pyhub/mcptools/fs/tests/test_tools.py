"""Tests for fs tools to ensure they work with core refactoring."""

from unittest.mock import AsyncMock, patch

import pytest

from pyhub.mcptools.fs.tools import fs__list_directory, fs__read_file, fs__write_file


class TestFsTools:
    """Test fs tools work correctly with core functions."""

    @pytest.mark.asyncio
    async def test_read_file_with_core(self):
        """Test fs__read_file uses core.read_file."""
        with patch("pyhub.mcptools.fs.tools.core.read_file", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = "test content"

            result = await fs__read_file(path="/test/file.txt")

            assert result == "test content"
            mock_read.assert_called_once_with("/test/file.txt")

    @pytest.mark.asyncio
    async def test_write_file_with_core(self):
        """Test fs__write_file uses core.write_file."""
        with patch("pyhub.mcptools.fs.tools.core.write_file", new_callable=AsyncMock) as mock_write:
            mock_write.return_value = "Successfully wrote to /test/file.txt"

            result = await fs__write_file(path="/test/file.txt", text_content="test content", text_encoding="utf-8")

            assert result == "Successfully wrote to /test/file.txt"
            mock_write.assert_called_once_with("/test/file.txt", "test content", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_write_file_base64_with_core(self):
        """Test fs__write_file uses core.write_file_base64 for base64 content."""
        with patch("pyhub.mcptools.fs.tools.core.write_file_base64", new_callable=AsyncMock) as mock_write:
            mock_write.return_value = "Successfully wrote to /test/file.bin"

            result = await fs__write_file(path="/test/file.bin", text_content="", base64_content="dGVzdCBjb250ZW50")

            assert result == "Successfully wrote to /test/file.bin"
            mock_write.assert_called_once_with("/test/file.bin", "dGVzdCBjb250ZW50")

    @pytest.mark.asyncio
    async def test_list_directory_with_core(self):
        """Test fs__list_directory uses core.list_directory."""
        with patch("pyhub.mcptools.fs.tools.core.list_directory", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"name": "file1.txt", "path": "file1.txt", "type": "file"},
                {"name": "dir1", "path": "dir1", "type": "directory"},
            ]

            result = await fs__list_directory(path="/test/dir", recursive=False, max_depth=0)

            assert "[FILE] file1.txt" in result
            assert "[DIR] dir1" in result
            mock_list.assert_called_once_with("/test/dir", False, 0)

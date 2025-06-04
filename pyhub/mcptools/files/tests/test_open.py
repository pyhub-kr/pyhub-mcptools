"""Tests for file open tool."""

from unittest.mock import AsyncMock, patch

import pytest

from pyhub.mcptools.files.tools.open import file__open


class TestFileOpen:
    """Test file__open tool."""

    @pytest.mark.asyncio
    async def test_open_file_success(self):
        """Test successful file opening."""
        with patch("pyhub.mcptools.files.tools.open.open_file_with_default_app", new_callable=AsyncMock) as mock_open:
            mock_open.return_value = "Successfully opened file with default application: /test/file.pdf"

            result = await file__open(path="/test/file.pdf", wait=False)

            assert "Successfully opened file" in result
            mock_open.assert_called_once_with("/test/file.pdf", False)

    @pytest.mark.asyncio
    async def test_open_file_with_wait(self):
        """Test opening file with wait option."""
        with patch("pyhub.mcptools.files.tools.open.open_file_with_default_app", new_callable=AsyncMock) as mock_open:
            mock_open.return_value = "Successfully opened file with default application: /test/file.xlsx"

            result = await file__open(path="/test/file.xlsx", wait=True)

            assert "Successfully opened file" in result
            mock_open.assert_called_once_with("/test/file.xlsx", True)

    @pytest.mark.asyncio
    async def test_open_file_not_found(self):
        """Test error when file doesn't exist."""
        with patch("pyhub.mcptools.files.tools.open.open_file_with_default_app", new_callable=AsyncMock) as mock_open:
            mock_open.side_effect = ValueError("File not found: /test/nonexistent.txt")

            with pytest.raises(ValueError, match="File not found"):
                await file__open(path="/test/nonexistent.txt")

    @pytest.mark.asyncio
    async def test_open_file_error(self):
        """Test error when file cannot be opened."""
        with patch("pyhub.mcptools.files.tools.open.open_file_with_default_app", new_callable=AsyncMock) as mock_open:
            mock_open.side_effect = ValueError("Failed to open file: some error")

            with pytest.raises(ValueError, match="Failed to open file"):
                await file__open(path="/test/file.txt")

"""Tests for files core functions."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from pyhub.mcptools.files.core import open_file_with_default_app


class TestOpenFileWithDefaultApp:
    """Test open_file_with_default_app function."""

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_validate.return_value = mock_path

            with pytest.raises(ValueError, match="File not found"):
                await open_file_with_default_app("/test/nonexistent.txt")

    @pytest.mark.asyncio
    async def test_path_is_directory(self):
        """Test error when path is a directory."""
        with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_file.return_value = False
            mock_validate.return_value = mock_path

            with pytest.raises(ValueError, match="Path is not a file"):
                await open_file_with_default_app("/test/directory")

    @pytest.mark.asyncio
    async def test_open_file_windows(self):
        """Test opening file on Windows."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Windows"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "C:\\test\\file.xlsx"
                mock_validate.return_value = mock_path

                # Mock os module with startfile
                mock_os = MagicMock()
                mock_os.startfile = MagicMock()

                with patch(
                    "builtins.__import__",
                    side_effect=lambda name, *args: mock_os if name == "os" else __import__(name, *args),
                ):
                    with patch("asyncio.to_thread") as mock_to_thread:
                        # Mock asyncio.to_thread to call the function immediately
                        mock_to_thread.side_effect = lambda func, *args: func(*args)

                        result = await open_file_with_default_app("C:\\test\\file.xlsx", wait=False)

                        assert "Successfully opened file" in result
                        # Verify os.startfile was called
                        mock_os.startfile.assert_called_once_with("C:\\test\\file.xlsx")

    @pytest.mark.asyncio
    async def test_open_file_windows_wait(self):
        """Test opening file on Windows with wait option."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Windows"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "C:\\test\\file.xlsx"
                mock_validate.return_value = mock_path

                with patch("subprocess.run") as mock_run:
                    with patch("asyncio.to_thread") as mock_to_thread:
                        # Mock asyncio.to_thread to call the function directly
                        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

                        result = await open_file_with_default_app("C:\\test\\file.xlsx", wait=True)

                        assert "Successfully opened file" in result
                        mock_run.assert_called_once_with(
                            ["cmd", "/c", "start", "/wait", "", "C:\\test\\file.xlsx"], shell=True, check=True
                        )

    @pytest.mark.asyncio
    async def test_open_file_macos(self):
        """Test opening file on macOS."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Darwin"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "/Users/test/file.pdf"
                mock_validate.return_value = mock_path

                with patch("subprocess.run") as mock_run:
                    with patch("asyncio.to_thread") as mock_to_thread:
                        # Mock asyncio.to_thread to call the function directly
                        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

                        result = await open_file_with_default_app("/Users/test/file.pdf", wait=False)

                        assert "Successfully opened file" in result
                        mock_run.assert_called_once_with(["open", "/Users/test/file.pdf"], check=True)

    @pytest.mark.asyncio
    async def test_open_file_macos_wait(self):
        """Test opening file on macOS with wait option."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Darwin"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "/Users/test/file.pdf"
                mock_validate.return_value = mock_path

                with patch("subprocess.run") as mock_run:
                    with patch("asyncio.to_thread") as mock_to_thread:
                        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

                        result = await open_file_with_default_app("/Users/test/file.pdf", wait=True)

                        assert "Successfully opened file" in result
                        mock_run.assert_called_once_with(["open", "-W", "/Users/test/file.pdf"], check=True)

    @pytest.mark.asyncio
    async def test_open_file_linux(self):
        """Test opening file on Linux."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Linux"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "/home/test/file.png"
                mock_validate.return_value = mock_path

                with patch("subprocess.run") as mock_run:
                    with patch("asyncio.to_thread") as mock_to_thread:
                        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

                        result = await open_file_with_default_app("/home/test/file.png", wait=False)

                        assert "Successfully opened file" in result
                        mock_run.assert_called_once_with(["xdg-open", "/home/test/file.png"], check=True)

    @pytest.mark.asyncio
    async def test_open_file_unsupported_os(self):
        """Test error on unsupported OS."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "UnknownOS"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_validate.return_value = mock_path

                with pytest.raises(ValueError, match="Unsupported operating system"):
                    await open_file_with_default_app("/test/file.txt")

    @pytest.mark.asyncio
    async def test_open_file_subprocess_error(self):
        """Test handling subprocess errors."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Darwin"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.__str__.return_value = "/test/file.txt"
                mock_validate.return_value = mock_path

                with patch("subprocess.run") as mock_run:
                    mock_run.side_effect = subprocess.CalledProcessError(1, "open")

                    with patch("asyncio.to_thread") as mock_to_thread:
                        mock_to_thread.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)

                        with pytest.raises(ValueError, match="Failed to open file"):
                            await open_file_with_default_app("/test/file.txt")

    @pytest.mark.asyncio
    async def test_open_file_windows_no_startfile(self):
        """Test error when os.startfile not available on non-Windows system."""
        with patch("pyhub.mcptools.files.core.platform.system") as mock_system:
            mock_system.return_value = "Windows"

            with patch("pyhub.mcptools.files.core.validate_path") as mock_validate:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_validate.return_value = mock_path

                # Mock os module without startfile
                mock_os = MagicMock()
                del mock_os.startfile  # Remove startfile attribute

                with patch(
                    "builtins.__import__",
                    side_effect=lambda name, *args: mock_os if name == "os" else __import__(name, *args),
                ):
                    with pytest.raises(ValueError, match="Cannot use Windows file opening on non-Windows system"):
                        await open_file_with_default_app("C:\\test\\file.xlsx", wait=False)

"""Tests for unified Outlook tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from pyhub.mcptools.microsoft.outlook.tools import outlook
from pyhub.mcptools.core.email_types import Email, EmailFolderType
import pyhub.mcptools.microsoft.outlook as outlook_module


@pytest.fixture
def sample_email():
    """Create a sample email for testing."""
    return Email(
        identifier="123456",
        subject="Test Email",
        sender_name="Test Sender",
        sender_email="sender@example.com",
        to="recipient@example.com",
        cc=None,
        received_at=datetime.now().isoformat(),
        body="This is a test email body",
        attachments=[],
    )


@pytest.fixture
def sample_email_list(sample_email):
    """Create a sample email list for testing."""
    return [sample_email]


@pytest.mark.asyncio
class TestUnifiedOutlookTool:
    """Test cases for the unified outlook tool."""

    async def test_list_operation_inbox(self, sample_email_list):
        """Test list operation for inbox folder."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            mock_run.return_value = sample_email_list

            result = await outlook(
                operation="list",
                max_hours=24,
                query="test",
                folder="inbox"
            )

            # Verify the function was called with correct parameters
            mock_run.assert_called_once()
            # Check positional args
            args = mock_run.call_args[0]
            assert args[0] == outlook_module.get_emails  # function
            # Check keyword args
            kwargs = mock_run.call_args[1]
            assert kwargs["max_hours"] == 24
            assert kwargs["query"] == "test"
            assert kwargs["email_folder_type"] == EmailFolderType.INBOX

            # Verify result contains email data
            assert "123456" in result
            assert "Test Email" in result
            assert "sender@example.com" in result

    async def test_list_operation_custom_folder(self, sample_email_list):
        """Test list operation for custom folder."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            mock_run.return_value = sample_email_list

            result = await outlook(
                operation="list",
                max_hours=48,
                folder="Important"
            )

            # Verify custom folder name was passed
            mock_run.assert_called_once()
            call_args = mock_run.call_args[1]
            assert call_args["email_folder_name"] == "Important"
            assert call_args["email_folder_type"] is None

    async def test_get_operation(self, sample_email):
        """Test get operation."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            mock_run.return_value = sample_email

            result = await outlook(
                operation="get",
                identifier="123456"
            )

            # Verify the function was called with correct identifier
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            assert args[0] == outlook_module.get_email  # function
            assert args[1] == "123456"  # identifier

            # Verify result contains email data
            assert "123456" in result
            assert "Test Email" in result

    async def test_get_operation_missing_identifier(self):
        """Test get operation with missing identifier."""
        # Don't call any backend functions when identifier is missing
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            # This should not be called due to validation
            mock_run.side_effect = Exception("Should not be called")

            result = await outlook(operation="get")

            # The function should return an error without calling the backend
            assert "error" in result
            assert "identifier is required" in result
            mock_run.assert_not_called()

    async def test_send_operation(self):
        """Test send operation."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            mock_run.return_value = "Email sent successfully"

            result = await outlook(
                operation="send",
                subject="Test Subject",
                message="Test Message",
                from_email="sender@example.com",
                recipient_list="recipient@example.com",
                html_message="<p>HTML content</p>",
                cc_list="cc@example.com",
                bcc_list="bcc@example.com",
                compose_only=False
            )

            # Verify the function was called with correct parameters
            mock_run.assert_called_once()
            call_args = mock_run.call_args[1]
            assert call_args["subject"] == "Test Subject"
            assert call_args["message"] == "Test Message"
            assert call_args["from_email"] == "sender@example.com"
            assert call_args["recipient_list"] == "recipient@example.com"
            assert call_args["html_message"] == "<p>HTML content</p>"
            assert call_args["cc_list"] == "cc@example.com"
            assert call_args["bcc_list"] == "bcc@example.com"
            assert call_args["compose_only"] is False

            assert result == "Email sent successfully"

    async def test_send_operation_compose_only(self):
        """Test send operation with compose_only flag."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            mock_run.return_value = "Compose window opened"

            result = await outlook(
                operation="send",
                subject="Test Subject",
                message="Test Message",
                from_email="sender@example.com",
                recipient_list="recipient@example.com",
                compose_only=True
            )

            # Verify compose_only was passed correctly
            call_args = mock_run.call_args[1]
            assert call_args["compose_only"] is True

            assert result == "Compose window opened"

    async def test_send_operation_missing_required_fields(self):
        """Test send operation with missing required fields."""
        # Don't call any backend functions when required fields are missing
        with patch("pyhub.mcptools.microsoft.outlook.tools.run_with_com_if_windows") as mock_run:
            # This should not be called due to validation
            mock_run.side_effect = Exception("Should not be called")

            result = await outlook(
                operation="send",
                subject="Test Subject"
                # Missing message, from_email, and recipient_list
            )

            # The function should return an error without calling the backend
            assert "error" in result
            assert "required for send operation" in result
            mock_run.assert_not_called()

    async def test_invalid_operation(self):
        """Test with invalid operation."""
        result = await outlook(operation="invalid")

        assert "error" in result
        assert "Unknown operation: invalid" in result

    async def test_windows_com_thread_execution(self):
        """Test that Windows COM thread execution works correctly."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.OS.current_is_windows") as mock_is_windows:
            mock_is_windows.return_value = True

            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = AsyncMock()
                mock_get_loop.return_value = mock_loop

                # Mock the executor result
                mock_loop.run_in_executor.return_value = []

                result = await outlook(
                    operation="list",
                    folder="inbox"
                )

                # Verify that run_in_executor was called for Windows
                mock_loop.run_in_executor.assert_called_once()

    async def test_macos_async_execution(self, sample_email_list):
        """Test that macOS uses regular async execution."""
        with patch("pyhub.mcptools.microsoft.outlook.tools.OS.current_is_windows") as mock_is_windows:
            mock_is_windows.return_value = False

            with patch("pyhub.mcptools.microsoft.outlook.tools.sync_to_async") as mock_sync_to_async:
                # Create a mock async function
                async_func = AsyncMock(return_value=sample_email_list)
                mock_sync_to_async.return_value = async_func

                result = await outlook(
                    operation="list",
                    folder="inbox"
                )

                # Verify sync_to_async was used for non-Windows
                mock_sync_to_async.assert_called_once()



"""Integration test to ensure Excel tools work with fs core functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyhub.mcptools.files.tools.excel import file__excel_read, file__excel_write


class TestExcelIntegration:
    """Test Excel tools integrated with fs core functions."""

    @pytest.mark.asyncio
    async def test_excel_write_read_cycle(self):
        """Test writing and reading Excel file using core functions."""
        test_data = "Name,Age,Score\nAlice,25,95\nBob,30,87"

        # Mock the fs core functions
        with patch("pyhub.mcptools.files.tools.excel.fs_core.write_file", new_callable=AsyncMock) as mock_write:
            with patch(
                "pyhub.mcptools.files.tools.excel.fs_core.read_file_binary", new_callable=AsyncMock
            ) as mock_read:
                # Setup mock for write
                mock_write.return_value = "Successfully wrote to /test/data.xlsx"

                # Setup mock for read - simulate no existing file (for overwrite check)
                mock_read.side_effect = [
                    ValueError("File not found"),  # First call for overwrite check
                    b"fake_excel_content",  # Second call for actual read
                ]

                # Mock openpyxl
                mock_openpyxl = MagicMock()
                with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
                    # Mock for write
                    mock_ws_write = MagicMock()
                    mock_ws_write.title = None
                    mock_ws_write.append = MagicMock()

                    mock_wb_write = MagicMock()
                    mock_wb_write.active = mock_ws_write
                    mock_wb_write.save = MagicMock()

                    # Mock for read
                    mock_ws_read = MagicMock()
                    mock_ws_read.min_row = 1
                    mock_ws_read.max_row = 3
                    mock_ws_read.min_column = 1
                    mock_ws_read.max_column = 3
                    mock_ws_read.iter_rows.return_value = [["Name", "Age", "Score"], ["Alice", 25, 95], ["Bob", 30, 87]]

                    mock_wb_read = MagicMock()
                    mock_wb_read.sheetnames = ["Sheet1"]
                    mock_wb_read.active = mock_ws_read

                    mock_openpyxl.Workbook.return_value = mock_wb_write
                    mock_openpyxl.load_workbook.return_value = mock_wb_read

                    # Test write
                    write_result = await file__excel_write(
                        file_path="/test/data.xlsx", data=test_data, sheet_name="TestData"
                    )

                    assert "저장되었습니다" in write_result
                    assert "/test/data.xlsx" in write_result

                    # Verify write was called with binary content
                    mock_write.assert_called_once()
                    call_args = mock_write.call_args
                    assert call_args[0][0] == "/test/data.xlsx"
                    assert isinstance(call_args[0][1], bytes)  # Should be binary content

                    # Reset read mock for actual read test
                    mock_read.reset_mock()
                    mock_read.side_effect = None
                    mock_read.return_value = b"fake_excel_content"

                    # Test read
                    read_result = await file__excel_read(file_path="/test/data.xlsx", sheet_name="", range="")

                    # Should get CSV formatted output
                    assert "Name,Age,Score" in read_result
                    assert "Alice,25,95" in read_result
                    assert "Bob,30,87" in read_result

                    # Verify read was called
                    mock_read.assert_called_once_with("/test/data.xlsx")

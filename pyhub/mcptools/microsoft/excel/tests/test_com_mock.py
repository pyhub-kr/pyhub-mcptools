"""
Mock-based tests for COM functionality that can run without Excel
"""
import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Only test on Windows
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="COM only available on Windows")


class TestCOMDecoratorsMocked:
    """Test COM decorators with mocked objects"""

    def test_com_retry_with_mock(self):
        """Test com_retry decorator logic without real COM"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.decorators import com_retry

        # Create a mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            "Success"
        ])

        # Apply decorator
        @com_retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()

        # Should succeed on third attempt
        result = test_func()
        assert result == "Success"
        assert mock_func.call_count == 3

    def test_com_error_handler_with_mock(self):
        """Test com_error_handler decorator"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.decorators import com_error_handler

        @com_error_handler(default_return="default_value")
        def failing_func():
            raise Exception("Test error")

        result = failing_func()
        assert result == "default_value"

    def test_release_com_object_with_mock(self):
        """Test release_com_object with mock COM object"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.decorators import release_com_object

        # Create mock COM object
        mock_obj = Mock()
        mock_obj._oleobj_ = Mock()

        # Should not raise exception
        release_com_object(mock_obj)
        mock_obj._oleobj_.Release.assert_called_once()

        # Test with None
        release_com_object(None)  # Should not raise


class TestExcelPoolMocked:
    """Test Excel pool with mocked COM objects"""

    @patch('win32com.client.Dispatch')
    def test_pool_instance_creation_mocked(self, mock_dispatch):
        """Test pool creates instances with mocked Excel"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.pool import ExcelPool

        # Setup mock Excel
        mock_excel = MagicMock()
        mock_excel.Visible = False
        mock_excel.Workbooks = MagicMock()
        mock_dispatch.return_value = mock_excel

        # Create pool
        pool = ExcelPool(min_size=0, max_size=2)

        # Create instance should work
        instance = pool._create_instance()
        assert instance is not None
        assert instance.app == mock_excel

        # Cleanup
        pool.shutdown()

    def test_pool_lifecycle_mocked(self):
        """Test pool lifecycle without real Excel"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.pool import ExcelPool, ExcelInstance

        # Create pool with no min instances
        pool = ExcelPool(min_size=0, max_size=3)

        # Create mock instance
        mock_app = Mock()
        mock_app.Visible = True
        instance = ExcelInstance(mock_app, 1)

        # Test instance methods
        instance.mark_used()
        assert instance.in_use is True

        instance.mark_free()
        assert instance.in_use is False

        instance.mark_error()
        assert instance.error_count == 1

        # Cleanup
        pool.shutdown()


class TestThreadSafetyMocked:
    """Test thread safety features with mocks"""

    def test_thread_state_management(self):
        """Test thread state without real COM"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.thread_safety import (
            get_thread_state, COMThreadState
        )

        # Get thread state
        state = get_thread_state()
        assert isinstance(state, COMThreadState)

        # Test app management
        mock_app = Mock()
        state.add_excel_app("test_app", mock_app)

        retrieved = state.get_excel_app("test_app")
        assert retrieved == mock_app

        # Test cleanup of dead refs
        state.cleanup_dead_refs()  # Should not raise

    @patch('pythoncom.CoInitialize')
    @patch('pythoncom.CoUninitialize')
    def test_com_initialization_mocked(self, mock_uninit, mock_init):
        """Test COM initialization with mocks"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.thread_safety import (
            ensure_com_initialized, cleanup_thread_com
        )

        # Test initialization
        result = ensure_com_initialized()
        assert result is True  # First time should return True
        mock_init.assert_called_once()

        # Second call should return False
        result = ensure_com_initialized()
        assert result is False

        # Test cleanup
        cleanup_thread_com()
        mock_uninit.assert_called_once()


class TestExcelWrappersMocked:
    """Test Excel wrapper classes with mocks"""

    @patch('pythoncom.CoInitialize')
    @patch('win32com.client.Dispatch')
    def test_excel_app_creation_mocked(self, mock_dispatch, mock_coinit):
        """Test ExcelApp creation with mocks"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.excel import ExcelApp

        # Setup mock
        mock_excel = MagicMock()
        mock_excel.Visible = True
        mock_excel.Workbooks = MagicMock()
        mock_excel.Workbooks.Count = 0
        mock_dispatch.return_value = mock_excel

        # Create app
        app = ExcelApp(visible=True, add_book=False)
        assert app._app == mock_excel
        assert app._com_initialized is True

        # Test property access
        books = app.books
        assert books is not None

    def test_range_operations_mocked(self):
        """Test Range operations with mocks"""
        if sys.platform != "win32":
            pytest.skip("Windows only test")

        from pyhub.mcptools.microsoft.excel.com.excel import Range

        # Create mock range
        mock_range = MagicMock()
        mock_range.Address = "A1:B2"
        mock_range.Value = ((1, 2), (3, 4))
        mock_range.Formula = "=SUM(A1:A2)"
        mock_range.Rows.Count = 2
        mock_range.Columns.Count = 2

        # Create Range wrapper
        range_obj = Range(mock_range)

        # Test properties
        assert range_obj.address == "A1:B2"
        assert range_obj.value == [[1, 2], [3, 4]]  # Converted to list
        assert range_obj.formula == "=SUM(A1:A2)"
        assert range_obj.shape == (2, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
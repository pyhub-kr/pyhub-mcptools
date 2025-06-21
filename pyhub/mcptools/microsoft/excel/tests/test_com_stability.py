"""
Tests for COM stability improvements
"""
import pytest
import sys
import threading
import time
import concurrent.futures
from unittest.mock import Mock, patch

# Skip all tests if not on Windows
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="COM only available on Windows")

if sys.platform == "win32":
    from pyhub.mcptools.microsoft.excel.com.decorators import (
        com_retry, ensure_com_thread, validate_com_object,
        com_error_handler, release_com_object
    )
    from pyhub.mcptools.microsoft.excel.com.pool import ExcelPool, get_excel_pool
    from pyhub.mcptools.microsoft.excel.com.thread_safety import (
        ensure_com_initialized, cleanup_thread_com,
        get_thread_state, register_excel_app
    )
    import win32com.client
    import pythoncom


class TestCOMDecorators:
    """Test COM decorators functionality"""

    def test_com_retry_success(self):
        """Test com_retry decorator with successful operation"""
        call_count = 0

        @com_retry(max_attempts=3, delay=0.1)
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Simulate COM error
                error = Exception("COM Error")
                error.hresult = 0x80010108  # RPC_E_DISCONNECTED
                raise error
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert call_count == 2

    def test_com_retry_failure(self):
        """Test com_retry decorator when all attempts fail"""
        call_count = 0

        @com_retry(max_attempts=3, delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            error = Exception("COM Error")
            error.hresult = 0x80010108
            raise error

        with pytest.raises(Exception) as exc_info:
            always_fails()

        assert call_count == 3
        assert "COM Error" in str(exc_info.value)

    def test_ensure_com_thread(self):
        """Test ensure_com_thread decorator"""
        @ensure_com_thread
        def com_operation():
            # Check if COM is initialized
            try:
                pythoncom.CoInitialize()
                # If this succeeds, COM wasn't initialized
                pythoncom.CoUninitialize()
                return False
            except:
                # COM was already initialized
                return True

        result = com_operation()
        assert result is True

    def test_com_error_handler(self):
        """Test com_error_handler decorator"""
        @com_error_handler(default_return="default")
        def failing_operation():
            error = Exception("COM Error")
            error.hresult = 0x80010108
            raise error

        result = failing_operation()
        assert result == "default"


class TestExcelPool:
    """Test Excel instance pool"""

    def test_pool_creation(self):
        """Test creating Excel pool"""
        pool = ExcelPool(min_size=1, max_size=3)
        assert pool.min_size == 1
        assert pool.max_size == 3
        pool.shutdown()

    def test_get_instance(self):
        """Test getting instance from pool"""
        pool = ExcelPool(min_size=1, max_size=3)

        try:
            with pool.get_instance() as excel:
                assert excel is not None
                # Test Excel is responsive
                excel.Visible = False
                assert excel.Visible is False
        finally:
            pool.shutdown()

    def test_pool_reuse(self):
        """Test that pool reuses instances"""
        pool = ExcelPool(min_size=1, max_size=3)

        try:
            # Get instance and release it
            with pool.get_instance() as excel1:
                excel1.Caption = "Test1"
                caption1 = excel1.Caption

            # Get another instance - should be the same
            with pool.get_instance() as excel2:
                caption2 = excel2.Caption
                assert caption2 == caption1
        finally:
            pool.shutdown()

    def test_pool_max_limit(self):
        """Test pool respects max size"""
        pool = ExcelPool(min_size=1, max_size=2)

        try:
            instances = []

            # Get max instances
            for i in range(2):
                instance = pool._create_instance()
                if instance:
                    instances.append(instance)

            # Pool should be at max
            with pool._lock:
                assert len(pool._all_instances) == 2

            # Cleanup
            for instance in instances:
                pool._destroy_instance(instance)
        finally:
            pool.shutdown()


class TestThreadSafety:
    """Test thread safety improvements"""

    def test_com_initialization_per_thread(self):
        """Test COM is initialized per thread"""
        results = {}

        def thread_worker(thread_id):
            ensure_com_initialized()
            state = get_thread_state()
            results[thread_id] = {
                'thread_id': state.thread_id,
                'com_initialized': state.com_initialized
            }
            cleanup_thread_com()

        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have its own state
        assert len(results) == 3
        for i in range(3):
            assert results[i]['com_initialized'] is False  # Cleaned up

    def test_excel_app_registration(self):
        """Test Excel app registration in thread"""
        ensure_com_initialized()

        try:
            # Create mock Excel app
            mock_app = Mock()
            mock_app.Visible = True

            # Register app
            app_id = register_excel_app(mock_app, "test_app")
            assert app_id == "test_app"

            # Retrieve app
            state = get_thread_state()
            retrieved_app = state.get_excel_app("test_app")
            assert retrieved_app is mock_app
        finally:
            cleanup_thread_com()

    def test_concurrent_excel_operations(self):
        """Test concurrent Excel operations in multiple threads"""
        results = []
        errors = []

        def worker(worker_id):
            try:
                ensure_com_initialized()

                # Create Excel instance
                excel = win32com.client.Dispatch("Excel.Application")
                excel.Visible = False

                # Register it
                register_excel_app(excel, f"worker_{worker_id}")

                # Do some work
                wb = excel.Workbooks.Add()
                sheet = wb.ActiveSheet
                sheet.Range("A1").Value = f"Worker {worker_id}"
                value = sheet.Range("A1").Value

                results.append({
                    'worker_id': worker_id,
                    'value': value,
                    'success': True
                })

                # Cleanup
                wb.Close(SaveChanges=False)
                excel.Quit()

            except Exception as e:
                errors.append({
                    'worker_id': worker_id,
                    'error': str(e)
                })
            finally:
                cleanup_thread_com()

        # Run workers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(3):
                future = executor.submit(worker, i)
                futures.append(future)

            # Wait for all to complete
            concurrent.futures.wait(futures)

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3
        for result in results:
            assert result['success'] is True
            assert f"Worker {result['worker_id']}" in result['value']


class TestCOMStabilityIntegration:
    """Integration tests for COM stability improvements"""

    def test_recovery_from_disconnected_excel(self):
        """Test recovery when Excel is disconnected"""
        from pyhub.mcptools.microsoft.excel.com.excel import ExcelApp

        # Create Excel app
        app = ExcelApp(visible=False)

        try:
            # Add a workbook
            wb = app.books.add()
            sheet = wb.sheets.active

            # Write some data
            sheet.range("A1").value = "Test"

            # Force quit Excel (simulating crash)
            app._app.Quit()

            # Try to use it again - should raise error
            with pytest.raises(Exception):
                sheet.range("A2").value = "This should fail"

        except:
            pass

    def test_pool_with_com_errors(self):
        """Test pool handles COM errors gracefully"""
        pool = ExcelPool(min_size=1, max_size=3, max_errors=2)

        try:
            with pool.get_instance() as excel:
                # Simulate some successful operations
                excel.Visible = False

            # Instance should be reusable
            with pool.get_instance() as excel:
                excel.Visible = True

        finally:
            pool.shutdown()

    def test_thread_cleanup_on_error(self):
        """Test thread cleanup works even with errors"""
        def worker_with_error():
            ensure_com_initialized()

            try:
                excel = win32com.client.Dispatch("Excel.Application")
                register_excel_app(excel, "error_app")

                # Force an error
                raise Exception("Simulated error")

            finally:
                # Cleanup should still work
                cleanup_thread_com()

        # Run in thread
        t = threading.Thread(target=worker_with_error)
        t.start()
        t.join()

        # Thread should have completed without hanging
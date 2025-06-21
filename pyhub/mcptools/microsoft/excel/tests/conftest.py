"""
Test configuration for Excel COM tests
"""
import sys
import pytest

def is_excel_available():
    """Check if Excel is available on the system"""
    if sys.platform != "win32":
        return False

    try:
        import win32com.client
        # Try to create Excel instance
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Quit()
        return True
    except:
        return False

# Skip all COM tests if Excel is not available
requires_excel = pytest.mark.skipif(
    not is_excel_available(),
    reason="Excel COM is not available (Windows with Excel required)"
)
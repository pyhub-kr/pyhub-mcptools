"""
Compatibility layer to switch between xlwings and COM implementation.
This allows gradual migration and testing.
"""
import os
import sys

# Environment variable to control implementation
USE_COM = os.environ.get('EXCEL_USE_COM', 'false').lower() == 'true'

if USE_COM and sys.platform == 'win32':
    try:
        # Use COM implementation
        from .excel import (
            ExcelApp as App,
            ExcelError,
            Workbook,
            Sheet,
            Range,
            Table
        )
        from .utils import (
            get_app,
            get_sheet,
            get_range,
            json_dumps,
            normalize_text,
            cleanup_excel_com,
            fix_data,
            get_workbooks_data
        )
    except ImportError:
        # Fall back to xlwings if COM import fails
        USE_COM = False

if USE_COM and sys.platform == 'win32':
    # Create module-level app instance
    def apps():
        """Get Excel application (compatibility with xlwings)"""
        return get_app()

    # Compatibility with xlwings books access
    class BooksProxy:
        @property
        def active(self):
            app = get_app()
            return app.active_book

        def __getitem__(self, key):
            app = get_app()
            return app.books[key]

    books = BooksProxy()

else:
    # Use xlwings implementation (default)
    try:
        import xlwings as xw
        from xlwings import App, Book as Workbook, Sheet, Range

        # Re-export xlwings functions
        apps = xw.apps
        books = xw.books

        # Import utility functions that work with xlwings
        from pyhub.mcptools.microsoft.excel.utils import (
            get_sheet,
            get_range,
            json_dumps,
            normalize_text,
            fix_data
        )

        def cleanup_excel_com():
            """No-op for xlwings"""
            pass

        def get_workbooks_data():
            """Get workbooks data using xlwings"""
            from pyhub.mcptools.microsoft.excel.utils import get_opened_workbooks_data
            return get_opened_workbooks_data()

        class ExcelError(Exception):
            """Excel error for xlwings compatibility"""
            pass

    except ImportError:
        raise ImportError("Neither xlwings nor pywin32 is available")
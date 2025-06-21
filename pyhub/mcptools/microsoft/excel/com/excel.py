"""
Direct COM interface for Excel operations without xlwings dependency.
This module provides a thin wrapper around win32com for Excel automation.
"""
import os
import sys
import logging
import weakref
from typing import Any, List, Optional, Union, Tuple
from pathlib import Path

# Check if we're on Windows
if sys.platform != "win32":
    raise ImportError("COM interface is only available on Windows")

try:
    import win32com.client
    from win32com.client import constants, Dispatch
    import pythoncom
    import pywintypes
except ImportError:
    raise ImportError("pywin32 is required for COM interface. Install with: pip install pywin32")

# Import decorators for COM safety
from .decorators import (
    com_retry,
    ensure_com_thread,
    validate_com_object,
    release_com_object,
    com_error_handler
)

# Set up logging
logger = logging.getLogger(__name__)

# Common COM error codes
RPC_E_DISCONNECTED = -2147417848  # 0x80010108
RPC_S_CALL_FAILED = -2147418110   # 0x800706be
RPC_S_SERVER_UNAVAILABLE = -2147418122  # 0x800706ba

def is_com_error(error):
    """Check if error is a COM disconnection error"""
    if hasattr(error, 'hresult'):
        return error.hresult in (RPC_E_DISCONNECTED, RPC_S_CALL_FAILED, RPC_S_SERVER_UNAVAILABLE)
    return False


class ExcelError(Exception):
    """Base exception for Excel COM operations"""
    pass


class ExcelApp:
    """Wrapper for Excel Application COM object"""

    def __init__(self, visible: bool = True, add_book: bool = False):
        """Initialize Excel application

        Args:
            visible: Whether Excel should be visible
            add_book: Whether to add a new workbook on startup
        """
        self._app = None
        self._com_initialized = False
        self._is_closed = False

        try:
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            self._com_initialized = True

            # Try to connect to existing Excel instance first
            try:
                self._app = win32com.client.GetActiveObject("Excel.Application")
                logger.info("Connected to existing Excel instance")
            except:
                # Create new instance if no existing instance
                self._app = win32com.client.Dispatch("Excel.Application")
                logger.info("Created new Excel instance")

            self._app.Visible = visible
            self._app.DisplayAlerts = False  # Suppress alerts

            if add_book and self._app.Workbooks.Count == 0:
                self._app.Workbooks.Add()

        except Exception as e:
            # Clean up COM if initialization failed
            if self._com_initialized:
                pythoncom.CoUninitialize()
                self._com_initialized = False
            raise ExcelError(f"Failed to initialize Excel application: {e}")

    @property
    def native(self):
        """Get native COM object"""
        return self._app

    def _ensure_alive(self):
        """Ensure the Excel application is still alive"""
        if self._is_closed:
            raise ExcelError("Excel application has been closed")
        try:
            # Try to access a property to check if alive
            _ = self._app.Visible
        except pywintypes.com_error as e:
            if is_com_error(e):
                self._is_closed = True
                raise ExcelError("Excel application has been disconnected. Please restart Excel.")
            raise

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def books(self):
        """Get workbooks collection"""
        self._ensure_alive()
        return WorkbooksCollection(self._app.Workbooks)

    @property
    @com_error_handler(default_return=None)
    def active_book(self):
        """Get active workbook"""
        self._ensure_alive()
        try:
            if self._app.ActiveWorkbook:
                return Workbook(self._app.ActiveWorkbook)
        except pywintypes.com_error as e:
            if is_com_error(e):
                return None
            raise
        return None

    def quit(self):
        """Quit Excel application"""
        if self._is_closed:
            return

        try:
            if self._app:
                # Close all workbooks without saving
                try:
                    workbook_count = self._app.Workbooks.Count
                    for i in range(workbook_count, 0, -1):
                        try:
                            self._app.Workbooks.Item(i).Close(SaveChanges=False)
                        except:
                            pass
                except:
                    pass

                # Quit Excel
                try:
                    self._app.Quit()
                except:
                    pass

                # Release COM object
                release_com_object(self._app)
                self._app = None

        except Exception as e:
            logger.warning(f"Error during Excel quit: {e}")
        finally:
            self._is_closed = True

            # Clean up COM
            if self._com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass
                self._com_initialized = False

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_com_initialized') and self._com_initialized and not self._is_closed:
                self.quit()
        except:
            pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.quit()
        return False


class WorkbooksCollection:
    """Wrapper for Workbooks collection"""

    def __init__(self, workbooks_com):
        self._workbooks = workbooks_com
        self._obj = workbooks_com  # For validate_com_object decorator

    @com_retry(max_attempts=2, delay=0.1)
    def __len__(self):
        return self._workbooks.Count

    @com_retry(max_attempts=2, delay=0.1)
    def __getitem__(self, key: Union[int, str]) -> 'Workbook':
        """Get workbook by index or name"""
        try:
            if isinstance(key, int):
                # COM collections are 1-indexed
                return Workbook(self._workbooks.Item(key + 1))
            else:
                return Workbook(self._workbooks.Item(key))
        except pywintypes.com_error as e:
            if is_com_error(e):
                raise ExcelError("Excel application has been disconnected")
            raise ExcelError(f"Workbook '{key}' not found: {e}")
        except Exception as e:
            raise ExcelError(f"Workbook '{key}' not found: {e}")

    @com_retry(max_attempts=2, delay=0.1)
    def add(self) -> 'Workbook':
        """Add new workbook"""
        return Workbook(self._workbooks.Add())

    @com_retry(max_attempts=2, delay=0.1)
    def open(self, filename: str) -> 'Workbook':
        """Open workbook from file"""
        path = Path(filename).resolve()
        if not path.exists():
            raise ExcelError(f"File not found: {filename}")
        return Workbook(self._workbooks.Open(str(path)))

    @property
    @com_error_handler(default_return=None)
    def active(self) -> 'Workbook':
        """Get active workbook"""
        active_wb = self._workbooks.Application.ActiveWorkbook
        return Workbook(active_wb) if active_wb else None


class Workbook:
    """Wrapper for Workbook COM object"""

    def __init__(self, workbook_com):
        self._workbook = workbook_com
        self._obj = workbook_com  # For validate_com_object decorator
        self._is_closed = False

    @property
    def native(self):
        """Get native COM object"""
        return self._workbook

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def name(self) -> str:
        """Get workbook name"""
        return self._workbook.Name

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def fullname(self) -> str:
        """Get full path of workbook"""
        return self._workbook.FullName

    @property
    def sheets(self):
        """Get sheets collection"""
        return SheetsCollection(self._workbook.Sheets)

    @com_retry(max_attempts=3, delay=0.5)
    def save(self):
        """Save workbook"""
        if self._is_closed:
            raise ExcelError("Workbook has been closed")
        self._workbook.Save()

    @com_retry(max_attempts=3, delay=0.5)
    def save_as(self, filename: str):
        """Save workbook as new file"""
        if self._is_closed:
            raise ExcelError("Workbook has been closed")
        self._workbook.SaveAs(filename)

    def close(self, save_changes: bool = False):
        """Close workbook"""
        if self._is_closed:
            return
        try:
            self._workbook.Close(SaveChanges=save_changes)
        finally:
            self._is_closed = True
            release_com_object(self._workbook)
            self._workbook = None

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_workbook') and self._workbook and not self._is_closed:
                self.close(save_changes=False)
        except:
            pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.close(save_changes=False)
        return False


class SheetsCollection:
    """Wrapper for Sheets collection"""

    def __init__(self, sheets_com):
        self._sheets = sheets_com
        self._obj = sheets_com  # For validate_com_object decorator

    @com_retry(max_attempts=2, delay=0.1)
    def __len__(self):
        return self._sheets.Count

    @com_retry(max_attempts=2, delay=0.1)
    def __getitem__(self, key: Union[int, str]) -> 'Sheet':
        """Get sheet by index or name"""
        try:
            if isinstance(key, int):
                # COM collections are 1-indexed
                return Sheet(self._sheets.Item(key + 1))
            else:
                return Sheet(self._sheets.Item(key))
        except Exception as e:
            raise ExcelError(f"Sheet '{key}' not found: {e}")

    @com_retry(max_attempts=2, delay=0.1)
    def add(self, name: Optional[str] = None, before: Optional[int] = None, after: Optional[int] = None) -> 'Sheet':
        """Add new sheet"""
        if before is not None:
            sheet_com = self._sheets.Add(Before=self._sheets.Item(before + 1))
        elif after is not None:
            sheet_com = self._sheets.Add(After=self._sheets.Item(after + 1))
        else:
            sheet_com = self._sheets.Add()

        if name:
            sheet_com.Name = name

        return Sheet(sheet_com)

    @property
    @com_error_handler(default_return=None)
    def active(self) -> 'Sheet':
        """Get active sheet"""
        active_sheet = self._sheets.Application.ActiveSheet
        return Sheet(active_sheet) if active_sheet else None


class Sheet:
    """Wrapper for Sheet COM object"""

    def __init__(self, sheet_com):
        self._sheet = sheet_com
        self._obj = sheet_com  # For validate_com_object decorator
        self._is_deleted = False

    @property
    def native(self):
        """Get native COM object"""
        return self._sheet

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def name(self) -> str:
        """Get sheet name"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        return self._sheet.Name

    @name.setter
    @com_retry(max_attempts=2, delay=0.1)
    def name(self, value: str):
        """Set sheet name"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        self._sheet.Name = value

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def index(self) -> int:
        """Get sheet index (0-based)"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        return self._sheet.Index - 1  # Convert to 0-based

    @com_retry(max_attempts=2, delay=0.1)
    def range(self, address: str) -> 'Range':
        """Get range by address"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        return Range(self._sheet.Range(address))

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def used_range(self) -> 'Range':
        """Get used range of sheet"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        return Range(self._sheet.UsedRange)

    @property
    def tables(self):
        """Get tables collection"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        return TablesCollection(self._sheet.ListObjects)

    def delete(self):
        """Delete sheet"""
        if self._is_deleted:
            return
        try:
            self._sheet.Delete()
        finally:
            self._is_deleted = True
            release_com_object(self._sheet)
            self._sheet = None

    @com_retry(max_attempts=2, delay=0.1)
    def activate(self):
        """Activate sheet"""
        if self._is_deleted:
            raise ExcelError("Sheet has been deleted")
        self._sheet.Activate()

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_sheet') and self._sheet and not self._is_deleted:
                release_com_object(self._sheet)
        except:
            pass


class Range:
    """Wrapper for Range COM object"""

    def __init__(self, range_com):
        self._range = range_com
        self._obj = range_com  # For validate_com_object decorator

    @property
    def native(self):
        """Get native COM object"""
        return self._range

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def address(self) -> str:
        """Get range address"""
        return self._range.Address

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def value(self) -> Any:
        """Get range value"""
        try:
            val = self._range.Value
            # Convert COM tuple of tuples to list of lists
            if isinstance(val, tuple):
                return [list(row) if isinstance(row, tuple) else row for row in val]
            return val
        except pywintypes.com_error as e:
            if is_com_error(e):
                raise ExcelError("Excel application has been disconnected")
            raise

    @value.setter
    @com_retry(max_attempts=3, delay=0.5)
    def value(self, val: Any):
        """Set range value"""
        try:
            self._range.Value = val
        except pywintypes.com_error as e:
            if is_com_error(e):
                raise ExcelError("Excel application has been disconnected")
            raise

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def formula(self) -> Any:
        """Get range formula"""
        return self._range.Formula

    @formula.setter
    @com_retry(max_attempts=3, delay=0.5)
    def formula(self, val: Any):
        """Set range formula"""
        self._range.Formula = val

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def shape(self) -> Tuple[int, int]:
        """Get range shape (rows, columns)"""
        return (self._range.Rows.Count, self._range.Columns.Count)

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def row(self) -> int:
        """Get first row number (1-based)"""
        return self._range.Row

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def column(self) -> int:
        """Get first column number (1-based)"""
        return self._range.Column

    @com_retry(max_attempts=2, delay=0.1)
    def expand(self, mode: str = "table") -> 'Range':
        """Expand range"""
        if mode == "table":
            return Range(self._range.CurrentRegion)
        elif mode == "down":
            last_row = self._range.End(constants.xlDown).Row
            return Range(self._range.Resize(last_row - self.row + 1, self._range.Columns.Count))
        elif mode == "right":
            last_col = self._range.End(constants.xlToRight).Column
            return Range(self._range.Resize(self._range.Rows.Count, last_col - self.column + 1))
        else:
            raise ValueError(f"Unknown expand mode: {mode}")

    @property
    def font(self):
        """Get font object"""
        return Font(self._range.Font)

    @property
    def interior(self):
        """Get interior object for fill color"""
        return Interior(self._range.Interior)

    @com_retry(max_attempts=2, delay=0.1)
    def clear(self):
        """Clear range contents"""
        self._range.Clear()

    @com_retry(max_attempts=2, delay=0.1)
    def clear_contents(self):
        """Clear only contents, not formatting"""
        self._range.ClearContents()

    @com_retry(max_attempts=2, delay=0.1)
    def autofit(self):
        """Autofit columns"""
        self._range.Columns.AutoFit()

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_range') and self._range:
                release_com_object(self._range)
        except:
            pass


class Font:
    """Wrapper for Font COM object"""

    def __init__(self, font_com):
        self._font = font_com
        self._obj = font_com  # For validate_com_object decorator

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def name(self) -> str:
        return self._font.Name

    @name.setter
    @com_retry(max_attempts=2, delay=0.1)
    def name(self, value: str):
        self._font.Name = value

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def size(self) -> float:
        return self._font.Size

    @size.setter
    @com_retry(max_attempts=2, delay=0.1)
    def size(self, value: float):
        self._font.Size = value

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def bold(self) -> bool:
        return self._font.Bold

    @bold.setter
    @com_retry(max_attempts=2, delay=0.1)
    def bold(self, value: bool):
        self._font.Bold = value

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def italic(self) -> bool:
        return self._font.Italic

    @italic.setter
    @com_retry(max_attempts=2, delay=0.1)
    def italic(self, value: bool):
        self._font.Italic = value

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def color(self) -> int:
        return self._font.Color

    @color.setter
    @com_retry(max_attempts=2, delay=0.1)
    def color(self, value: int):
        """Set color using RGB integer"""
        self._font.Color = value

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_font') and self._font:
                release_com_object(self._font)
        except:
            pass


class Interior:
    """Wrapper for Interior COM object"""

    def __init__(self, interior_com):
        self._interior = interior_com
        self._obj = interior_com  # For validate_com_object decorator

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def color(self) -> int:
        return self._interior.Color

    @color.setter
    @com_retry(max_attempts=2, delay=0.1)
    def color(self, value: int):
        """Set color using RGB integer"""
        self._interior.Color = value

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_interior') and self._interior:
                release_com_object(self._interior)
        except:
            pass


class TablesCollection:
    """Wrapper for Tables (ListObjects) collection"""

    def __init__(self, tables_com):
        self._tables = tables_com
        self._obj = tables_com  # For validate_com_object decorator

    @com_retry(max_attempts=2, delay=0.1)
    def __len__(self):
        return self._tables.Count

    @com_retry(max_attempts=2, delay=0.1)
    def __getitem__(self, key: Union[int, str]) -> 'Table':
        """Get table by index or name"""
        try:
            if isinstance(key, int):
                return Table(self._tables.Item(key + 1))
            else:
                return Table(self._tables.Item(key))
        except Exception as e:
            raise ExcelError(f"Table '{key}' not found: {e}")

    @com_retry(max_attempts=2, delay=0.1)
    def add(self, source_range: Range, name: str, has_headers: bool = True) -> 'Table':
        """Add new table"""
        table_com = self._tables.Add(
            SourceType=1,  # xlSrcRange
            Source=source_range.native,
            XlListObjectHasHeaders=1 if has_headers else 2
        )
        table_com.Name = name
        return Table(table_com)

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_tables') and self._tables:
                release_com_object(self._tables)
        except:
            pass


class Table:
    """Wrapper for Table (ListObject) COM object"""

    def __init__(self, table_com):
        self._table = table_com
        self._obj = table_com  # For validate_com_object decorator
        self._is_deleted = False

    @property
    @com_retry(max_attempts=2, delay=0.1)
    def name(self) -> str:
        if self._is_deleted:
            raise ExcelError("Table has been deleted")
        return self._table.Name

    @name.setter
    @com_retry(max_attempts=2, delay=0.1)
    def name(self, value: str):
        if self._is_deleted:
            raise ExcelError("Table has been deleted")
        self._table.Name = value

    @property
    def range(self) -> Range:
        """Get table range"""
        if self._is_deleted:
            raise ExcelError("Table has been deleted")
        return Range(self._table.Range)

    @property
    def data_body_range(self) -> Range:
        """Get data body range (excluding headers)"""
        if self._is_deleted:
            raise ExcelError("Table has been deleted")
        return Range(self._table.DataBodyRange)

    def delete(self):
        """Delete table"""
        if self._is_deleted:
            return
        try:
            self._table.Delete()
        finally:
            self._is_deleted = True
            release_com_object(self._table)
            self._table = None

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if hasattr(self, '_table') and self._table and not self._is_deleted:
                release_com_object(self._table)
        except:
            pass


# Utility functions
def rgb_to_int(r: int, g: int, b: int) -> int:
    """Convert RGB values to Windows color integer"""
    return r + (g * 256) + (b * 256 * 256)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


@ensure_com_thread
def cleanup_com():
    """Cleanup COM references and force garbage collection"""
    import gc
    # Force garbage collection to release COM objects
    gc.collect()
    # Give COM some time to release objects
    import time
    time.sleep(0.1)

    # Log cleanup
    logger.info("COM cleanup completed")
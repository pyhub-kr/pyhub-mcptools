"""
Utility functions for COM-based Excel operations.
Provides compatibility layer to match xlwings interface.
"""
import json
import logging
import threading
from typing import Any, Optional, Union, List
from .excel import (
    ExcelApp, Workbook, Sheet, Range,
    hex_to_rgb, rgb_to_int
)
from .thread_safety import (
    get_thread_safe_excel,
    ensure_com_initialized,
    register_excel_app,
    get_thread_excel_app,
    cleanup_thread_com
)
from .decorators import com_retry, ensure_com_thread, com_error_handler

logger = logging.getLogger(__name__)

# Thread-local storage for caching wrapped apps
_thread_local = threading.local()

# Main app ID for thread-local Excel instance
_MAIN_APP_ID = "main_excel_app"


@ensure_com_thread
@com_retry(max_attempts=3)
def get_app() -> ExcelApp:
    """Get or create Excel application instance

    This maintains a single Excel instance per thread to avoid COM issues.
    Uses the thread-safe pool for better resource management.
    """
    # First try to get existing wrapped app from thread registry
    wrapped_app = getattr(_thread_local, 'wrapped_app', None)
    if wrapped_app and hasattr(wrapped_app, '_app'):
        try:
            # Verify it's still alive
            _ = wrapped_app._app.Visible
            return wrapped_app
        except Exception:
            # App is dead, will create new one
            logger.warning("Cached Excel app is dead, creating new one")
            _thread_local.wrapped_app = None

    # Try to get COM app from thread registry
    com_app = get_thread_excel_app(_MAIN_APP_ID)
    if com_app:
        try:
            # Verify it's still alive
            _ = com_app.Visible
            # Create wrapper and cache it
            wrapped_app = _create_wrapped_app(com_app)
            _thread_local.wrapped_app = wrapped_app
            return wrapped_app
        except Exception:
            # App is dead, will create new one
            logger.warning("Registry Excel app is dead, creating new one")

    # Create new Excel app using thread-safe method
    try:
        com_app = get_thread_safe_excel()
        com_app.Visible = True

        # Register it for this thread
        register_excel_app(com_app, _MAIN_APP_ID)

        # Create wrapper and cache it
        wrapped_app = _create_wrapped_app(com_app)
        _thread_local.wrapped_app = wrapped_app
        return wrapped_app
    except Exception as e:
        logger.error(f"Failed to create Excel app: {e}")
        raise


def _create_wrapped_app(com_app) -> ExcelApp:
    """Create ExcelApp wrapper from COM object

    Creates a lightweight wrapper around an existing COM Excel application.
    This wrapper doesn't own the COM initialization since it's managed by
    the thread safety layer.
    """
    # Create a minimal wrapper that uses the existing COM object
    wrapper = ExcelApp.__new__(ExcelApp)
    wrapper._app = com_app
    wrapper._com_initialized = False  # We don't own COM initialization
    wrapper._is_closed = False

    # Add the books property dynamically since we can't use the normal init
    # This ensures the wrapper has all the necessary properties
    return wrapper


def close_cached_app():
    """Close the cached Excel application for the current thread"""
    try:
        # Clear wrapped app cache
        if hasattr(_thread_local, 'wrapped_app'):
            _thread_local.wrapped_app = None

        # Get COM app from registry
        app = get_thread_excel_app(_MAIN_APP_ID)
        if app:
            try:
                # Close all workbooks first
                for wb in app.Workbooks:
                    wb.Close(SaveChanges=False)
            except:
                pass

            try:
                app.Quit()
            except:
                pass

        # Cleanup thread COM resources
        cleanup_thread_com()
    except Exception as e:
        logger.error(f"Error closing cached app: {e}")


@ensure_com_thread
@com_retry(max_attempts=2)
def get_sheet(
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Sheet:
    """Get sheet by book and sheet name, matching xlwings interface

    Args:
        book_name: Name of the workbook. If None, uses active workbook.
        sheet_name: Name of the sheet. If None, uses active sheet.

    Returns:
        Sheet object

    Raises:
        ValueError: If no active workbook when book_name is None
        KeyError: If specified book or sheet not found
    """
    app = get_app()

    try:
        if book_name:
            book = app.books[book_name]
        else:
            book = app.active_book
            if not book:
                raise ValueError("No active workbook")

        if sheet_name:
            sheet = book.sheets[sheet_name]
        else:
            sheet = book.sheets.active

        return sheet
    except Exception as e:
        logger.error(f"Error getting sheet (book={book_name}, sheet={sheet_name}): {e}")
        raise


@ensure_com_thread
@com_retry(max_attempts=2)
def get_range(
    sheet_range: str,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    expand_mode: Optional[str] = None,
) -> Range:
    """Get range by address, matching xlwings interface

    Args:
        sheet_range: Range address (e.g., "A1", "A1:C10", "Sheet1!A1")
        book_name: Name of the workbook. If None, uses active workbook.
        sheet_name: Name of the sheet. If None, uses active sheet or parses from range.
        expand_mode: If specified, expands range ('table', 'down', 'right')

    Returns:
        Range object

    Raises:
        ValueError: If range specification is invalid
    """
    try:
        # Parse sheet name from range if present (e.g., "Sheet1!A1")
        if sheet_range and "!" in sheet_range:
            parsed_sheet_name, sheet_range = sheet_range.split("!", 1)
            sheet_name = sheet_name or parsed_sheet_name

        # If expand_mode is specified, extract starting cell only
        if expand_mode:
            sheet_range = sheet_range.split(":", 1)[0]

        sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)

        if sheet_range:
            range_ = sheet.range(sheet_range)
        else:
            range_ = sheet.used_range

        if expand_mode:
            range_ = range_.expand(mode=expand_mode)

        return range_
    except Exception as e:
        logger.error(f"Error getting range '{sheet_range}': {e}")
        raise


def json_dumps(data: Any) -> str:
    """JSON dumps with proper formatting"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    return text.strip().lower()


def parse_hex_color(hex_color: str) -> int:
    """Convert hex color string to Windows color integer"""
    if not hex_color or not hex_color.startswith('#'):
        return 0

    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_int(r, g, b)


def cleanup_excel_com():
    """Cleanup Excel COM objects and cached app

    This function ensures proper cleanup of all COM resources,
    including cached Excel applications and thread-local COM state.
    """
    try:
        # Close cached app first
        close_cached_app()

        # Then general COM cleanup
        from .excel import cleanup_com
        cleanup_com()

        logger.info("Excel COM cleanup completed")
    except Exception as e:
        logger.error(f"Error during Excel COM cleanup: {e}")


def fix_data(sheet_range: str, values: Union[str, list]) -> Union[str, list]:
    """
    Fix data format for Excel range, matching xlwings behavior.

    If sheet_range is a column range and values is a flat list,
    convert to nested list for proper column orientation.
    """
    import re

    if (
        isinstance(values, str)
        or not isinstance(values, list)
        or (isinstance(values, list) and values and isinstance(values[0], list))
    ):
        return values

    # Check if range contains a range specification
    range_pattern = (
        r"(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?"
    )
    match = re.match(range_pattern, sheet_range)

    if not match:
        return values

    # Extract start and end cells
    start_cell = match.group(1)
    end_cell = match.group(2)

    # Single cell case
    if not end_cell:
        return values

    # Check if it's a column range (e.g., A1:A10)
    start_col = re.search(r"[A-Z]+", start_cell).group(0)
    end_col = re.search(r"[A-Z]+", end_cell).group(0)

    # If same column, convert flat list to nested list
    if start_col == end_col and isinstance(values, list) and not isinstance(values[0], list):
        return [[val] for val in values]

    return values


@ensure_com_thread
@com_error_handler(default_return={"books": []})
def get_workbooks_data() -> dict:
    """Get data about all open workbooks

    Returns a dictionary containing information about all open workbooks
    and their sheets. Handles errors gracefully to avoid breaking the UI.

    Returns:
        Dictionary with 'books' key containing list of workbook data
    """
    app = get_app()

    workbooks_data = {
        "books": []
    }

    try:
        for i in range(len(app.books)):
            try:
                book = app.books[i]
                book_data = {
                    "name": book.name,
                    "fullname": book.fullname,
                    "sheets": [],
                    "active": app.active_book and book.name == app.active_book.name
                }

                for j in range(len(book.sheets)):
                    try:
                        sheet = book.sheets[j]

                        # Safely get used range
                        try:
                            used_range = sheet.used_range
                            if used_range:
                                range_address = used_range.address
                                range_shape = list(used_range.shape)
                                range_count = used_range.shape[0] * used_range.shape[1]
                            else:
                                range_address = None
                                range_shape = [0, 0]
                                range_count = 0
                        except Exception:
                            # Handle case where sheet has no data
                            range_address = None
                            range_shape = [0, 0]
                            range_count = 0

                        sheet_data = {
                            "name": sheet.name,
                            "index": sheet.index,
                            "range": range_address,
                            "count": range_count,
                            "shape": range_shape,
                            "active": book.sheets.active.name == sheet.name
                        }
                        book_data["sheets"].append(sheet_data)
                    except Exception as e:
                        logger.warning(f"Error getting sheet data for sheet {j}: {e}")
                        continue

                workbooks_data["books"].append(book_data)
            except Exception as e:
                logger.warning(f"Error getting workbook data for book {i}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error iterating workbooks: {e}")

    return workbooks_data
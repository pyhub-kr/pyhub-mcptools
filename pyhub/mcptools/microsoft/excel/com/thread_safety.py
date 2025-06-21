"""Enhanced thread safety for COM operations"""
import threading
import pythoncom
import logging
import weakref
from typing import Dict, Any, Optional, Set
from contextlib import contextmanager
import atexit

logger = logging.getLogger(__name__)

# Thread-local storage for COM state and resources
_thread_local = threading.local()

# Global lock for thread-safe operations
_global_lock = threading.RLock()

# Track COM initialized threads
_com_threads: Dict[int, Dict[str, Any]] = {}

# Track all Excel app instances across threads
_all_excel_apps: Set[weakref.ref] = set()


class COMThreadState:
    """Manages COM state for a thread"""

    def __init__(self, thread_id: int):
        self.thread_id = thread_id
        self.com_initialized = False
        self.excel_apps: Dict[str, weakref.ref] = {}
        self.initialization_count = 0
        self.error_count = 0

    def add_excel_app(self, app_id: str, app: Any):
        """Add an Excel app to this thread's registry"""
        self.excel_apps[app_id] = weakref.ref(app)

    def get_excel_app(self, app_id: str) -> Optional[Any]:
        """Get an Excel app from this thread's registry"""
        ref = self.excel_apps.get(app_id)
        if ref:
            app = ref()
            if app is None:
                # Weak reference died, remove it
                del self.excel_apps[app_id]
            return app
        return None

    def cleanup_dead_refs(self):
        """Remove dead weak references"""
        dead_keys = [
            app_id for app_id, ref in self.excel_apps.items()
            if ref() is None
        ]
        for key in dead_keys:
            del self.excel_apps[key]


def get_thread_state() -> COMThreadState:
    """Get or create thread state"""
    thread_id = threading.get_ident()

    if not hasattr(_thread_local, 'state'):
        with _global_lock:
            if thread_id not in _com_threads:
                _com_threads[thread_id] = COMThreadState(thread_id)
            _thread_local.state = _com_threads[thread_id]

    return _thread_local.state


def ensure_com_initialized() -> bool:
    """
    Ensure COM is initialized for the current thread

    Returns:
        True if newly initialized, False if already initialized
    """
    state = get_thread_state()

    if not state.com_initialized:
        with _global_lock:
            if not state.com_initialized:
                try:
                    pythoncom.CoInitialize()
                    state.com_initialized = True
                    state.initialization_count += 1
                    logger.debug(f"COM initialized for thread {state.thread_id}")
                    return True
                except Exception as e:
                    state.error_count += 1
                    logger.error(f"Failed to initialize COM for thread {state.thread_id}: {e}")
                    raise

    return False


def cleanup_thread_com():
    """Cleanup COM for the current thread"""
    state = get_thread_state()

    with _global_lock:
        # First, cleanup Excel apps
        for app_id, ref in list(state.excel_apps.items()):
            try:
                app = ref()
                if app:
                    logger.debug(f"Cleaning up Excel app {app_id} in thread {state.thread_id}")
                    try:
                        # Close all workbooks
                        for wb in app.Workbooks:
                            wb.Close(SaveChanges=False)
                    except:
                        pass

                    try:
                        app.Quit()
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error cleaning up Excel app {app_id}: {e}")

        state.excel_apps.clear()

        # Then uninitialize COM
        if state.com_initialized:
            try:
                pythoncom.CoUninitialize()
                state.com_initialized = False
                logger.debug(f"COM cleaned up for thread {state.thread_id}")
            except Exception as e:
                logger.error(f"Error uninitializing COM for thread {state.thread_id}: {e}")


@contextmanager
def com_thread_context():
    """
    Context manager for COM operations

    Ensures COM is initialized and provides cleanup on exit
    """
    newly_initialized = ensure_com_initialized()
    try:
        yield
    finally:
        # Only cleanup if we initialized COM in this context
        if newly_initialized:
            cleanup_thread_com()


def register_excel_app(app: Any, app_id: Optional[str] = None) -> str:
    """
    Register an Excel app instance for tracking

    Args:
        app: Excel application COM object
        app_id: Optional ID for the app

    Returns:
        The app ID used for registration
    """
    if app_id is None:
        app_id = f"excel_{id(app)}"

    state = get_thread_state()
    state.add_excel_app(app_id, app)

    # Also track globally with weak reference
    with _global_lock:
        _all_excel_apps.add(weakref.ref(app))

    logger.debug(f"Registered Excel app {app_id} in thread {state.thread_id}")
    return app_id


def get_thread_excel_app(app_id: str) -> Optional[Any]:
    """Get an Excel app registered to the current thread"""
    state = get_thread_state()
    return state.get_excel_app(app_id)


def cleanup_all_threads():
    """Cleanup COM for all threads (call on shutdown)"""
    with _global_lock:
        logger.info("Cleaning up COM for all threads")

        # Cleanup all tracked Excel apps
        for ref in list(_all_excel_apps):
            try:
                app = ref()
                if app:
                    try:
                        app.Quit()
                    except:
                        pass
            except:
                pass

        _all_excel_apps.clear()

        # Note: We can't uninitialize COM for other threads
        # They need to do it themselves
        # We can only clean up the current thread
        try:
            cleanup_thread_com()
        except:
            pass


# Register cleanup on exit
atexit.register(cleanup_all_threads)


class ThreadSafeExcelPool:
    """Thread-safe pool for Excel instances"""

    def __init__(self, max_per_thread: int = 3):
        self.max_per_thread = max_per_thread
        self._lock = threading.Lock()

    def get_or_create_app(self, visible: bool = False) -> Any:
        """Get or create an Excel app for the current thread"""
        state = get_thread_state()
        ensure_com_initialized()

        # Clean up dead references first
        state.cleanup_dead_refs()

        # Try to reuse existing app
        for app_id, ref in state.excel_apps.items():
            app = ref()
            if app:
                try:
                    # Check if app is responsive
                    _ = app.Visible
                    logger.debug(f"Reusing Excel app {app_id}")
                    return app
                except:
                    # App is dead, will be cleaned up
                    pass

        # Create new app if under limit
        if len(state.excel_apps) < self.max_per_thread:
            try:
                import win32com.client
                app = win32com.client.Dispatch("Excel.Application")
                app.Visible = visible
                app.DisplayAlerts = False

                app_id = register_excel_app(app)
                logger.info(f"Created new Excel app {app_id}")
                return app
            except Exception as e:
                logger.error(f"Failed to create Excel app: {e}")
                raise
        else:
            raise RuntimeError(
                f"Thread {state.thread_id} has reached max Excel apps limit ({self.max_per_thread})"
            )


# Global thread-safe Excel pool
_excel_pool = ThreadSafeExcelPool()


def get_thread_safe_excel() -> Any:
    """Get a thread-safe Excel instance"""
    return _excel_pool.get_or_create_app()
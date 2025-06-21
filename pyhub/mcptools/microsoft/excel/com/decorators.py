"""
Decorators for COM safety and stability
"""
import functools
import time
import logging
import pythoncom
from typing import Callable, Any, TypeVar, Optional
import win32com.client

logger = logging.getLogger(__name__)

T = TypeVar('T')

# COM error codes
COM_ERRORS = {
    0x80010108: "RPC_E_DISCONNECTED",
    0x800706BE: "RPC_S_CALL_FAILED",
    0x800706BA: "RPC_S_SERVER_UNAVAILABLE",
    0x80004005: "E_FAIL",
    0x80070005: "E_ACCESSDENIED",
}


def com_retry(max_attempts: int = 3, delay: float = 0.5, backoff: float = 2.0) -> Callable:
    """
    Decorator to retry COM operations with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_code = getattr(e, 'hresult', None) or getattr(e, 'hr', None)
                    error_name = COM_ERRORS.get(error_code, "UNKNOWN")

                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"COM operation failed (attempt {attempt + 1}/{max_attempts}): "
                            f"{error_name} ({error_code}). Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff

                        # Try to reinitialize COM if disconnected
                        if error_code in (0x80010108, 0x800706BA):
                            try:
                                pythoncom.CoUninitialize()
                                pythoncom.CoInitialize()
                                logger.info("COM reinitialized after disconnect")
                            except:
                                pass
                    else:
                        logger.error(
                            f"COM operation failed after {max_attempts} attempts: "
                            f"{error_name} ({error_code})"
                        )

            raise last_exception

        return wrapper
    return decorator


def ensure_com_thread(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure COM is initialized for the current thread
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        com_initialized = False
        try:
            # Check if COM is already initialized
            pythoncom.CoInitialize()
            com_initialized = True
        except:
            # COM was already initialized
            pass

        try:
            return func(*args, **kwargs)
        finally:
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass

    return wrapper


def validate_com_object(obj_name: str = "COM object") -> Callable:
    """
    Decorator to validate COM object is still connected

    Args:
        obj_name: Name of the object for error messages
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            # Check if object has _app or similar COM reference
            com_obj = getattr(self, '_app', None) or getattr(self, '_obj', None)

            if com_obj is None:
                raise RuntimeError(f"{obj_name} is not initialized")

            # Try to access a property to check if still connected
            try:
                # Common COM object property that should always exist
                if hasattr(com_obj, 'Name'):
                    _ = com_obj.Name
                elif hasattr(com_obj, 'Visible'):
                    _ = com_obj.Visible
            except Exception as e:
                error_code = getattr(e, 'hresult', None) or getattr(e, 'hr', None)
                if error_code in (0x80010108, 0x800706BA, 0x800706BE):
                    raise RuntimeError(f"{obj_name} is disconnected") from e
                raise

            return func(self, *args, **kwargs)

        return wrapper
    return decorator


def release_com_object(obj: Any) -> None:
    """
    Safely release a COM object

    Args:
        obj: COM object to release
    """
    if obj is not None:
        try:
            # Try to release the COM object
            if hasattr(obj, '_oleobj_'):
                obj._oleobj_.Release()
        except:
            pass

        # Clear Python reference
        try:
            del obj
        except:
            pass


def com_error_handler(default_return: Any = None) -> Callable:
    """
    Decorator to handle COM errors gracefully

    Args:
        default_return: Value to return if COM operation fails
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_code = getattr(e, 'hresult', None) or getattr(e, 'hr', None)
                error_name = COM_ERRORS.get(error_code, "UNKNOWN")

                logger.error(
                    f"COM operation '{func.__name__}' failed: "
                    f"{error_name} ({error_code}): {str(e)}"
                )

                return default_return

        return wrapper
    return decorator
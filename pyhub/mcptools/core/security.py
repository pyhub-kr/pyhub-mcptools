"""Security utilities for MCP tools."""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Union

logger = logging.getLogger(__name__)


def sanitize_for_logging(data: Any, max_length: int = 100) -> str:
    """Sanitize data for safe logging.

    Args:
        data: Data to sanitize
        max_length: Maximum length of string representation

    Returns:
        Safe string representation of data
    """
    if data is None:
        return "None"

    if isinstance(data, (list, tuple)):
        return f"[{len(data)} items]"

    if isinstance(data, dict):
        return f"{{dict with {len(data)} keys}}"

    if isinstance(data, str):
        if len(data) > max_length:
            return f"string[{len(data)} chars]"
        # Check for potential sensitive patterns
        if any(pattern in data.lower() for pattern in ["password", "secret", "token", "key"]):
            return "***REDACTED***"
        return data

    # For other types, convert to string and check length
    str_repr = str(data)
    if len(str_repr) > max_length:
        return f"{type(data).__name__}[{len(str_repr)} chars]"

    return str_repr


def secure_log_params(func: Callable) -> Callable:
    """Decorator to log function calls with sanitized parameters.

    Logs function entry and exit with sanitized parameter values
    to prevent sensitive data leakage in logs.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__

        # Sanitize args and kwargs for logging
        safe_args = [sanitize_for_logging(arg) for arg in args]
        safe_kwargs = {k: sanitize_for_logging(v) for k, v in kwargs.items()}

        logger.debug(f"Entering {func_name} with args={safe_args}, kwargs={safe_kwargs}")

        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Exiting {func_name} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func_name}: {type(e).__name__}: {str(e)}")
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__

        # Sanitize args and kwargs for logging
        safe_args = [sanitize_for_logging(arg) for arg in args]
        safe_kwargs = {k: sanitize_for_logging(v) for k, v in kwargs.items()}

        logger.debug(f"Entering {func_name} with args={safe_args}, kwargs={safe_kwargs}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func_name} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func_name}: {type(e).__name__}: {str(e)}")
            raise

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def mask_sensitive_fields(data: Union[dict, list], sensitive_keys: list = None) -> Union[dict, list]:
    """Mask sensitive fields in data structures.

    Args:
        data: Data structure to mask
        sensitive_keys: List of keys to mask (default: common sensitive keys)

    Returns:
        Copy of data with sensitive fields masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password",
            "secret",
            "token",
            "key",
            "api_key",
            "access_token",
            "refresh_token",
            "client_secret",
            "private_key",
            "credentials",
        ]

    # Convert to lowercase for case-insensitive matching
    sensitive_keys_lower = [k.lower() for k in sensitive_keys]

    def _mask_dict(d: dict) -> dict:
        masked = {}
        for key, value in d.items():
            if any(sk in key.lower() for sk in sensitive_keys_lower):
                masked[key] = "***REDACTED***"
            elif isinstance(value, dict):
                masked[key] = _mask_dict(value)
            elif isinstance(value, list):
                masked[key] = _mask_list(value)
            else:
                masked[key] = value
        return masked

    def _mask_list(lst: list) -> list:
        masked = []
        for item in lst:
            if isinstance(item, dict):
                masked.append(_mask_dict(item))
            elif isinstance(item, list):
                masked.append(_mask_list(item))
            else:
                masked.append(item)
        return masked

    if isinstance(data, dict):
        return _mask_dict(data)
    elif isinstance(data, list):
        return _mask_list(data)
    else:
        return data


def sanitize_input(input_str: str) -> str:
    """Sanitize user input for security.

    Args:
        input_str: Input string to sanitize

    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return str(input_str)

    # Remove null bytes and control characters
    sanitized = input_str.replace("\x00", "").replace("\r", "").replace("\n", " ")

    # Strip whitespace
    sanitized = sanitized.strip()

    # Limit length to prevent DoS
    if len(sanitized) > 10000:
        sanitized = sanitized[:10000]

    return sanitized

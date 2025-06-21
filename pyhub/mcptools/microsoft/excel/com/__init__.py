"""
COM interface for Excel - Direct Windows COM access without xlwings
"""
import sys

# Only expose modules on Windows
if sys.platform == "win32":
    try:
        from . import excel
        from . import utils
        from . import decorators
        from . import pool
        from . import thread_safety
        from . import compat

        __all__ = ['excel', 'utils', 'decorators', 'pool', 'thread_safety', 'compat']
    except ImportError:
        # If imports fail even on Windows, provide empty list
        __all__ = []
else:
    __all__ = []
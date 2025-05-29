"""Python sandbox implementation for secure code execution."""

import ast
import sys
import io
import contextlib
import multiprocessing
import signal
import base64
import traceback
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import tempfile

# Import allowed modules at module level
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None

import json
import csv
import math
import statistics
import datetime
import re
from collections import defaultdict, Counter


class SecurityError(Exception):
    """Raised when code contains security violations."""
    pass


def _execute_code_worker(code: str, safe_builtins: dict, allowed_modules: dict) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """Execute code in restricted environment (worker function for multiprocessing)."""
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()

    # Create restricted import function
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        """Restricted import function."""
        if name in allowed_modules:
            module = allowed_modules[name]
            if isinstance(module, dict) and fromlist:
                # Handle 'from module import item' for collections
                result = type(sys)('restricted_module')
                for item in fromlist:
                    if item in module:
                        setattr(result, item, module[item])
                    else:
                        raise ImportError(f"Cannot import '{item}' from '{name}'")
                return result
            return module
        else:
            raise ImportError(f"Import of '{name}' is not allowed")

    globals_dict = {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
        '__doc__': None,
        '__package__': None,
        '__import__': safe_import,
    }

    # Pre-import common modules for convenience if available
    if 'pd' in allowed_modules:
        globals_dict['pd'] = allowed_modules['pd']
    if 'np' in allowed_modules:
        globals_dict['np'] = allowed_modules['np']
    if 'plt' in allowed_modules:
        globals_dict['plt'] = allowed_modules['plt']
    if 'sns' in allowed_modules:
        globals_dict['sns'] = allowed_modules['sns']

    # Temporary directory for any plots
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        plot_path = temp_path / "plot.png"

        # Inject plot saving logic
        globals_dict['_plot_path'] = str(plot_path)

        try:
            with contextlib.redirect_stdout(output_buffer):
                with contextlib.redirect_stderr(error_buffer):
                    # Execute the code
                    exec(code, globals_dict)

                    # Check if a plot was created
                    if 'plt' in globals_dict and globals_dict['plt'] is not None:
                        plt_module = globals_dict['plt']
                        if hasattr(plt_module, 'get_fignums') and plt_module.get_fignums():
                            plt_module.savefig(plot_path, dpi=150, bbox_inches='tight')
                            plt_module.close('all')

            # Read plot if it exists
            image_base64 = None
            if plot_path.exists():
                with open(plot_path, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')

            return output_buffer.getvalue(), image_base64, {}

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return output_buffer.getvalue(), None, {'error': error_msg}


class PythonSandbox:
    """Secure Python code execution environment."""

    def __init__(self):
        # Safe built-in functions
        self.safe_builtins = {
            # Type constructors
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
            'frozenset': frozenset, 'bytes': bytes, 'bytearray': bytearray,

            # Math and data
            'abs': abs, 'min': min, 'max': max, 'sum': sum, 'round': round,
            'len': len, 'sorted': sorted, 'reversed': reversed,
            'range': range, 'enumerate': enumerate, 'zip': zip,

            # Type checking
            'isinstance': isinstance, 'type': type,

            # String operations
            'chr': chr, 'ord': ord,

            # Boolean
            'all': all, 'any': any,

            # Other safe functions
            'print': print, 'repr': repr, 'hash': hash,
            'filter': filter, 'map': map,

            # Exceptions (safe ones)
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'KeyError': KeyError,
            'IndexError': IndexError,
            'AttributeError': AttributeError,
        }

        # Allowed modules with safe imports
        self.allowed_modules = {
            # Standard library (safe parts)
            'math': math,
            'statistics': statistics,
            'datetime': datetime,
            'json': json,
            'csv': csv,
            're': re,

            # Collections
            'collections': {'defaultdict': defaultdict, 'Counter': Counter},
        }

        # Add optional modules if available
        if pd is not None:
            self.allowed_modules.update({
                'pandas': pd,
                'pd': pd,
            })

        if np is not None:
            self.allowed_modules.update({
                'numpy': np,
                'np': np,
            })

        if matplotlib is not None:
            self.allowed_modules.update({
                'matplotlib': matplotlib,
                'matplotlib.pyplot': plt,
                'plt': plt,
            })

        if sns is not None:
            self.allowed_modules.update({
                'seaborn': sns,
                'sns': sns,
            })

        # Dangerous patterns to check
        self.dangerous_patterns = [
            # System access
            'os.', 'sys.', 'subprocess.', 'socket.', 'shutil.',

            # File operations
            'open(', 'file(', 'input(', 'raw_input(',

            # Code execution
            'eval(', 'exec(', 'compile(', '__import__(',

            # Introspection that could be dangerous
            '__class__', '__bases__', '__subclasses__', '__code__',
            '__globals__', '__builtins__',

            # Network
            'urllib', 'requests', 'http.client',

            # Process/thread
            'threading', 'multiprocessing', 'concurrent',
        ]

    def _check_code_safety(self, code: str) -> None:
        """Check if code contains dangerous patterns."""
        # Basic string pattern check
        code_lower = code.lower()
        for pattern in self.dangerous_patterns:
            if pattern.lower() in code_lower:
                raise SecurityError(f"Dangerous pattern detected: {pattern}")

        # AST-based analysis
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax: {e}")

        # Check for dangerous AST nodes
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.allowed_modules:
                        raise SecurityError(f"Import of '{alias.name}' is not allowed")

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module not in self.allowed_modules:
                    # Check if it's a submodule of allowed module
                    allowed = False
                    for allowed_module in self.allowed_modules:
                        if module.startswith(allowed_module + '.'):
                            allowed = True
                            break
                    if not allowed:
                        raise SecurityError(f"Import from '{module}' is not allowed")

            # Check for attribute access to dangerous objects
            elif isinstance(node, ast.Attribute):
                if node.attr in ['__class__', '__bases__', '__subclasses__', '__code__', '__globals__']:
                    raise SecurityError(f"Access to '{node.attr}' is not allowed")

    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code in sandboxed environment.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with keys:
                - output: stdout output
                - error: error message if any
                - image: base64 encoded image if plot was generated
        """
        # Security check
        try:
            self._check_code_safety(code)
        except (SecurityError, SyntaxError) as e:
            return {'error': str(e)}

        # Execute in separate process with timeout
        with multiprocessing.Pool(1) as pool:
            try:
                result = pool.apply_async(
                    _execute_code_worker,
                    args=(code, self.safe_builtins.copy(), self.allowed_modules.copy())
                )
                output, image, error_dict = result.get(timeout=timeout)

                response = {'output': output}
                if image:
                    response['image'] = image
                if error_dict.get('error'):
                    response['error'] = error_dict['error']

                return response

            except multiprocessing.TimeoutError:
                pool.terminate()
                return {'error': f'Code execution timed out after {timeout} seconds'}
            except Exception as e:
                return {'error': f'Execution failed: {str(e)}'}


def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Convenience function to execute Python code."""
    sandbox = PythonSandbox()
    return sandbox.execute(code, timeout)

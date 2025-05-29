"""Python sandbox implementation using subprocess for better isolation."""

import ast
import sys
import json
import base64
import subprocess
import tempfile
import os
from typing import Any, Dict, Optional
from pathlib import Path


class SecurityError(Exception):
    """Raised when code contains security violations."""
    pass


class PythonSandbox:
    """Secure Python code execution environment using subprocess."""

    def __init__(self):
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

        # Allowed imports
        self.allowed_imports = {
            'math', 'statistics', 'datetime', 'json', 'csv', 're', 'io',
            'collections', 'pandas', 'pd', 'numpy', 'np',
            'matplotlib', 'matplotlib.pyplot', 'plt',
            'seaborn', 'sns'
        }

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
                    if alias.name not in self.allowed_imports:
                        raise SecurityError(f"Import of '{alias.name}' is not allowed")

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module not in self.allowed_imports:
                    # Check if it's a submodule of allowed module
                    allowed = False
                    for allowed_module in self.allowed_imports:
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
        """Execute Python code in sandboxed subprocess.

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

        # Write code to temp file to avoid escaping issues
        code_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                code_file = f.name

            # Create the sandbox script
            sandbox_script = f'''
import sys
import io
import json
import base64
import tempfile
from pathlib import Path
import os

# Restrict builtins
safe_builtins = {{
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'frozenset': frozenset, 'bytes': bytes, 'bytearray': bytearray,
    'abs': abs, 'min': min, 'max': max, 'sum': sum, 'round': round,
    'len': len, 'sorted': sorted, 'reversed': reversed,
    'range': range, 'enumerate': enumerate, 'zip': zip,
    'isinstance': isinstance, 'type': type,
    'chr': chr, 'ord': ord,
    'all': all, 'any': any,
    'print': print, 'repr': repr, 'hash': hash,
    'filter': filter, 'map': map,
    'Exception': Exception, 'ValueError': ValueError,
    'TypeError': TypeError, 'KeyError': KeyError,
    'IndexError': IndexError, 'AttributeError': AttributeError,
}}

# Create a safe import function
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    allowed_modules = {{
        'math', 'statistics', 'datetime', 'json', 'csv', 're', 'io',
        'collections', 'pandas', 'pd', 'numpy', 'np',
        'matplotlib', 'matplotlib.pyplot', 'plt', 'seaborn', 'sns'
    }}

    if name in allowed_modules or any(name.startswith(m + '.') for m in allowed_modules):
        return original_import(name, globals, locals, fromlist, level)
    else:
        raise ImportError(f"Import of '{{name}}' is not allowed")

# Save original import
original_import = __import__

# Add safe import to builtins
safe_builtins['__import__'] = safe_import

# Override __builtins__
__builtins__ = safe_builtins

# Import allowed modules
import math
import statistics
import datetime
import json as json_module
import csv
import re
import io as io_module
from collections import defaultdict, Counter
from io import StringIO

# Try to import optional modules
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
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None

# Capture output
output_buffer = io.StringIO()
sys.stdout = output_buffer
sys.stderr = output_buffer

result = {{'output': '', 'error': None, 'image': None}}

# Create temp directory for plots
temp_dir = tempfile.mkdtemp()
plot_path = Path(temp_dir) / "plot.png"

try:
    # Read and execute user code
    with open('{code_file}', 'r') as f:
        user_code = f.read()
    exec(user_code)

    # Check if plot was created
    if plt is not None and plt.get_fignums():
        plt.savefig(str(plot_path), dpi=150, bbox_inches='tight')
        plt.close('all')

        # Read and encode plot
        if plot_path.exists():
            with open(plot_path, 'rb') as f:
                result['image'] = base64.b64encode(f.read()).decode('utf-8')

    result['output'] = output_buffer.getvalue()

except Exception as e:
    import traceback
    result['error'] = f"{{type(e).__name__}}: {{str(e)}}\\n{{traceback.format_exc()}}"
    result['output'] = output_buffer.getvalue()

# Clean up
import shutil
shutil.rmtree(temp_dir, ignore_errors=True)

# Delete the code file
try:
    os.unlink('{code_file}')
except:
    pass

# Output result as JSON
sys.stdout = sys.__stdout__
print(json.dumps(result))
'''

            # Run in subprocess
            try:
                proc = subprocess.run(
                    [sys.executable, '-c', sandbox_script],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if proc.stdout:
                    try:
                        return json.loads(proc.stdout)
                    except json.JSONDecodeError:
                        return {
                            'output': proc.stdout,
                            'error': f'Failed to parse output: {proc.stderr}'
                        }
                else:
                    return {'error': proc.stderr or 'No output produced'}

            except subprocess.TimeoutExpired:
                return {'error': f'Code execution timed out after {timeout} seconds'}
            except Exception as e:
                return {'error': f'Execution failed: {str(e)}'}
        finally:
            # Clean up the temp file if it still exists
            if code_file and Path(code_file).exists():
                try:
                    os.unlink(code_file)
                except:
                    pass


def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Convenience function to execute Python code."""
    sandbox = PythonSandbox()
    return sandbox.execute(code, timeout)

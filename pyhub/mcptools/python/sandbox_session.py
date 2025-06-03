"""Python sandbox with session support."""

import ast
import sys
import json
import base64
import subprocess
import tempfile
import os
import pickle
import time
from typing import Any, Dict, Optional
from pathlib import Path

from .session_manager import SessionManager


class SecurityError(Exception):
    """Raised when code contains security violations."""
    pass


class SessionAwarePythonSandbox:
    """Python code execution with session state management."""

    def __init__(self):
        # Initialize session manager
        self.session_manager = SessionManager()

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

    def execute(self, code: str, session_id: Optional[str] = None,
                reset_session: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code with optional session state.

        Args:
            code: Python code to execute
            session_id: Optional session ID for state persistence
            reset_session: Whether to reset the session before execution
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with keys:
                - output: stdout output
                - error: error message if any
                - image: base64 encoded image if plot was generated
                - session_id: session ID used
        """
        start_time = time.time()

        # Security check
        try:
            self._check_code_safety(code)
        except (SecurityError, SyntaxError) as e:
            return {'error': str(e)}

        # Handle session
        if session_id:
            # Create session if needed
            session_id = self.session_manager.create_session(session_id)

            # Reset if requested
            if reset_session:
                self.session_manager.clear_session(session_id)

            # Load existing variables
            session_vars = self.session_manager.load_variables(session_id)
        else:
            session_vars = {}

        # Write code and session state to temp files
        code_file = None
        state_file = None
        output_state_file = None

        try:
            # Write code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                code_file = f.name

            # Write session state
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
                pickle.dump(session_vars, f)
                state_file = f.name

            # Create output state file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
                output_state_file = f.name

            # Create the sandbox script
            sandbox_script = self._create_sandbox_script(
                code_file, state_file, output_state_file
            )

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
                        result = json.loads(proc.stdout)

                        # Load updated state if session is used
                        if session_id and Path(output_state_file).exists():
                            try:
                                with open(output_state_file, 'rb') as f:
                                    new_namespace = pickle.load(f)
                                self.session_manager.save_variables(session_id, new_namespace)
                            except Exception as e:
                                print(f"Failed to save session state: {e}")

                        # Add session_id to result
                        result['session_id'] = session_id

                        # Save execution history
                        if session_id:
                            execution_time_ms = int((time.time() - start_time) * 1000)
                            self.session_manager.save_execution(
                                session_id, code,
                                result.get('output', ''),
                                result.get('error'),
                                execution_time_ms
                            )

                        return result

                    except json.JSONDecodeError:
                        return {
                            'output': proc.stdout,
                            'error': f'Failed to parse output: {proc.stderr}',
                            'session_id': session_id
                        }
                else:
                    return {
                        'error': proc.stderr or 'No output produced',
                        'session_id': session_id
                    }

            except subprocess.TimeoutExpired:
                return {
                    'error': f'Code execution timed out after {timeout} seconds',
                    'session_id': session_id
                }
            except Exception as e:
                return {
                    'error': f'Execution failed: {str(e)}',
                    'session_id': session_id
                }
        finally:
            # Clean up temp files
            for file_path in [code_file, state_file, output_state_file]:
                if file_path and Path(file_path).exists():
                    try:
                        os.unlink(file_path)
                    except:
                        pass

    def _create_sandbox_script(self, code_file: str, state_file: str,
                              output_state_file: str) -> str:
        """Create the sandbox execution script."""
        return f'''
import sys
import io
import json
import base64
import tempfile
import pickle
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

# Load session state
namespace = {{}}
try:
    with open('{state_file}', 'rb') as f:
        namespace = pickle.load(f)
except Exception:
    pass

# Add imported modules to namespace
namespace.update({{
    'math': math,
    'statistics': statistics,
    'datetime': datetime,
    'json': json_module,
    'csv': csv,
    're': re,
    'io': io_module,
    'defaultdict': defaultdict,
    'Counter': Counter,
    'StringIO': StringIO,
}})

if pd is not None:
    namespace['pd'] = pd
    namespace['pandas'] = pd
if np is not None:
    namespace['np'] = np
    namespace['numpy'] = np
if plt is not None:
    namespace['plt'] = plt
    namespace['matplotlib'] = matplotlib
if sns is not None:
    namespace['sns'] = sns
    namespace['seaborn'] = sns

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
    exec(user_code, namespace)

    # Check if plot was created
    if plt is not None and plt.get_fignums():
        plt.savefig(str(plot_path), dpi=150, bbox_inches='tight')
        plt.close('all')

        # Read and encode plot
        if plot_path.exists():
            with open(plot_path, 'rb') as f:
                result['image'] = base64.b64encode(f.read()).decode('utf-8')

    result['output'] = output_buffer.getvalue()

    # Save updated namespace (excluding modules and functions)
    clean_namespace = {{}}
    for key, value in namespace.items():
        if key.startswith('_'):
            continue
        if hasattr(value, '__module__') and hasattr(value, '__name__'):
            continue
        if callable(value) and hasattr(value, '__code__'):
            continue
        try:
            pickle.dumps(value)
            clean_namespace[key] = value
        except:
            pass

    with open('{output_state_file}', 'wb') as f:
        pickle.dump(clean_namespace, f)

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

# Global instance for session consistency
_sandbox_instance = None

def get_sandbox() -> SessionAwarePythonSandbox:
    """Get or create the global sandbox instance."""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = SessionAwarePythonSandbox()
    return _sandbox_instance

def execute_python_with_session(code: str, session_id: Optional[str] = None,
                               reset_session: bool = False, timeout: int = 30) -> Dict[str, Any]:
    """Convenience function to execute Python code with session support."""
    sandbox = get_sandbox()
    return sandbox.execute(code, session_id, reset_session, timeout)
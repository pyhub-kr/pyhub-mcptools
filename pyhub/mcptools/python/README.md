# Python REPL MCP Tool

A secure Python REPL (Read-Eval-Print Loop) tool for Claude Desktop that enables data analysis and visualization capabilities.

## Features

- **Secure Execution**: Code runs in an isolated subprocess with restricted access
- **Data Analysis**: Full support for pandas, numpy, and statistical operations
- **Visualization**: Create plots with matplotlib and seaborn (when installed)
- **Safety First**: No file system access, no network access, no dangerous operations

## Supported Libraries

- `pandas` (pd) - Data manipulation and analysis
- `numpy` (np) - Numerical computing
- `matplotlib.pyplot` (plt) - Plotting and visualization
- `seaborn` (sns) - Statistical data visualization
- `math` - Mathematical functions
- `statistics` - Statistical functions
- `datetime` - Date and time operations
- `json` - JSON data handling
- `csv` - CSV file operations
- `re` - Regular expressions
- `collections` - Counter, defaultdict
- `io` - StringIO for data loading

## Security Features

- **Restricted Imports**: Only whitelisted modules can be imported
- **No System Access**: Cannot access os, sys, subprocess, etc.
- **No File Access**: Cannot read or write files
- **No Network Access**: Cannot make network requests
- **Execution Timeout**: Configurable timeout (default 30s, max 300s)
- **Process Isolation**: Runs in separate subprocess

## Usage Examples

### Basic Python Execution
```python
result = await python_repl(
    code="print('Hello, World!')\nprint(2 + 2)",
    timeout_seconds=5
)
```

### Data Analysis with Pandas
```python
code = """
import pandas as pd

data = {
    'product': ['A', 'B', 'C'],
    'sales': [100, 150, 80],
    'profit': [20, 35, 15]
}

df = pd.DataFrame(data)
print("Sales Summary:")
print(df.describe())
print(f"\\nTotal profit: ${df['profit'].sum()}")
"""

result = await python_repl(code=code)
```

### Creating Visualizations
```python
code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine Wave')
plt.grid(True)
plt.legend()
"""

result = await python_repl(code=code)
# result will contain a base64-encoded PNG image
```

### Using python_analyze_data Tool

The `python_analyze_data` tool provides convenient shortcuts for common data analysis tasks:

```python
# Basic statistics
result = await python_analyze_data(
    data="name,age,score\\nAlice,25,85\\nBob,30,92",
    analysis_type="describe"
)

# Custom analysis
result = await python_analyze_data(
    data=csv_data,
    analysis_type="custom",
    custom_code="print(df.groupby('category').mean())"
)
```

## Installation

The Python tool is included with pyhub-mcptools. To enable visualization features:

```bash
pip install "pyhub-mcptools[python]"
```

This installs the optional dependencies:
- pandas
- numpy
- matplotlib
- seaborn

## Technical Details

### Sandbox Implementation

The sandbox uses a subprocess-based approach for better isolation:

1. **Code Validation**: AST parsing to detect dangerous patterns
2. **Subprocess Execution**: Runs in separate Python process
3. **Restricted Builtins**: Only safe built-in functions available
4. **Import Control**: Custom import function that checks whitelist
5. **Output Capture**: Captures stdout, stderr, and generated plots

### Return Format

All tools return a JSON string with the following structure:

```json
{
    "output": "stdout output from the code",
    "error": "error message if any",
    "image": "base64-encoded PNG if plot was created"
}
```

## Limitations

- Cannot access files or network resources
- Limited to whitelisted libraries only
- Maximum execution time of 300 seconds
- Memory limited by subprocess constraints
- No interactive input (input() not allowed)
- No threading or multiprocessing
- No code execution functions (eval, exec)

## Error Handling

The tool provides clear error messages for:
- Syntax errors in Python code
- Import of disallowed modules
- Use of dangerous patterns
- Execution timeouts
- Missing optional dependencies
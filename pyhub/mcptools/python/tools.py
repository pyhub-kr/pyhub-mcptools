"""Python REPL MCP tools."""

import asyncio
from typing import Literal, Optional

from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.python.sandbox_subprocess import execute_python
from pyhub.mcptools.core.json_utils import json_dumps


@mcp.tool(
    timeout=60,
    enabled=settings.USE_PYTHON_TOOLS,
)
async def python_repl(
    code: str = Field(
        description="Python code to execute. Supports pandas, numpy, matplotlib, seaborn, etc.",
        examples=[
            "import pandas as pd\ndf = pd.DataFrame({'A': [1,2,3], 'B': [4,5,6]})\nprint(df)",
            "import matplotlib.pyplot as plt\nplt.plot([1,2,3], [4,5,6])\nplt.title('Test')",
        ],
    ),
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time in seconds",
        ge=1,
        le=300,
    ),
) -> str:
    """Execute Python code in a secure sandbox environment.

    This tool provides a secure Python REPL for data analysis and visualization.

    Supported libraries:
    - pandas (pd): Data manipulation and analysis
    - numpy (np): Numerical computing
    - matplotlib.pyplot (plt): Plotting and visualization
    - seaborn (sns): Statistical data visualization
    - math, statistics: Mathematical functions
    - datetime: Date and time operations
    - json, csv: Data formats
    - re: Regular expressions
    - collections: defaultdict, Counter

    Security features:
    - Restricted imports (no os, sys, subprocess, etc.)
    - No file system access
    - No network access
    - Execution timeout
    - Memory limits via process isolation

    Returns:
        JSON string with:
        - output: stdout output from the code
        - error: error message if execution failed
        - image: base64 encoded PNG if matplotlib plot was created

    Examples:
        Data analysis:
        ```python
        import pandas as pd
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'score': [85, 92, 78]
        })
        print(df.describe())
        print(f"Average age: {df['age'].mean()}")
        ```

        Visualization:
        ```python
        import matplotlib.pyplot as plt
        import numpy as np

        x = np.linspace(0, 2*np.pi, 100)
        y = np.sin(x)

        plt.figure(figsize=(10, 6))
        plt.plot(x, y, 'b-', label='sin(x)')
        plt.plot(x, np.cos(x), 'r--', label='cos(x)')
        plt.xlabel('x')
        plt.ylabel('y')
        plt.title('Trigonometric Functions')
        plt.legend()
        plt.grid(True)
        ```
    """
    # Execute in thread pool to avoid blocking
    result = await asyncio.to_thread(execute_python, code=code, timeout=timeout_seconds)

    return json_dumps(result)


@mcp.tool(
    timeout=60,
    enabled=settings.USE_PYTHON_TOOLS,
)
async def python_analyze_data(
    data: str = Field(
        description="Data in CSV or JSON format",
        examples=[
            "name,age,score\\nAlice,25,85\\nBob,30,92\\nCharlie,35,78",
            '[{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]',
        ],
    ),
    analysis_type: Literal["describe", "correlation", "plot", "custom"] = Field(
        default="describe",
        description="Type of analysis to perform",
    ),
    custom_code: Optional[str] = Field(
        default=None,
        description="Custom analysis code (when analysis_type='custom'). Variable 'df' contains the data.",
    ),
    plot_type: Optional[Literal["histogram", "scatter", "line", "bar", "box", "heatmap"]] = Field(
        default="histogram",
        description="Type of plot to create (when analysis_type='plot')",
    ),
    columns: Optional[str] = Field(
        default=None,
        description="Comma-separated column names for analysis",
    ),
) -> str:
    """Analyze data using pandas and create visualizations.

    This is a convenience tool that loads data and performs common analyses.
    For more complex analysis, use python_repl directly.

    Returns:
        JSON string with analysis results and/or visualizations
    """
    # Build the analysis code
    code_parts = ["import pandas as pd", "import numpy as np"]

    # Only import plotting libraries if needed
    if analysis_type == "plot" or analysis_type == "correlation":
        code_parts.extend(["import matplotlib.pyplot as plt", "import seaborn as sns"])

    # Load data
    if data.strip().startswith("[") or data.strip().startswith("{"):
        # JSON data
        code_parts.append(f"import json")
        code_parts.append(f"data = json.loads('''{data}''')")
        code_parts.append("df = pd.DataFrame(data)")
    else:
        # CSV data
        code_parts.append("from io import StringIO")
        code_parts.append(f"csv_data = '''{data}'''")
        code_parts.append("df = pd.read_csv(StringIO(csv_data))")

    # Perform analysis based on type
    if analysis_type == "describe":
        code_parts.append("print('Data Shape:', df.shape)")
        code_parts.append("print('\\nData Types:')")
        code_parts.append("print(df.dtypes)")
        code_parts.append("print('\\nBasic Statistics:')")
        code_parts.append("print(df.describe())")
        code_parts.append("print('\\nMissing Values:')")
        code_parts.append("print(df.isnull().sum())")

    elif analysis_type == "correlation":
        code_parts.append("# Select numeric columns")
        code_parts.append("numeric_df = df.select_dtypes(include=[np.number])")
        code_parts.append("if not numeric_df.empty:")
        code_parts.append("    print('Correlation Matrix:')")
        code_parts.append("    print(numeric_df.corr())")
        code_parts.append("    plt.figure(figsize=(10, 8))")
        code_parts.append("    sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', center=0)")
        code_parts.append("    plt.title('Correlation Heatmap')")
        code_parts.append("else:")
        code_parts.append("    print('No numeric columns found for correlation analysis')")

    elif analysis_type == "plot":
        if columns:
            cols = [col.strip() for col in columns.split(",")]
        else:
            cols = None

        if plot_type == "histogram":
            code_parts.append("numeric_df = df.select_dtypes(include=[np.number])")
            code_parts.append("if not numeric_df.empty:")
            if cols:
                code_parts.append(f"    cols_to_plot = [c for c in {cols} if c in numeric_df.columns]")
                code_parts.append("    if cols_to_plot:")
                code_parts.append("        numeric_df = numeric_df[cols_to_plot]")
            code_parts.append("    n_cols = len(numeric_df.columns)")
            code_parts.append("    n_rows = (n_cols + 1) // 2")
            code_parts.append("    fig, axes = plt.subplots(n_rows, 2, figsize=(12, 4*n_rows))")
            code_parts.append("    axes = axes.flatten() if n_cols > 1 else [axes]")
            code_parts.append("    for i, col in enumerate(numeric_df.columns):")
            code_parts.append("        if i < len(axes):")
            code_parts.append("            numeric_df[col].hist(ax=axes[i], bins=20)")
            code_parts.append("            axes[i].set_title(f'Distribution of {col}')")
            code_parts.append("    for j in range(i+1, len(axes)):")
            code_parts.append("        axes[j].set_visible(False)")
            code_parts.append("    plt.tight_layout()")

        elif plot_type == "scatter" and cols and len(cols) >= 2:
            code_parts.append(f"plt.figure(figsize=(10, 6))")
            code_parts.append(f"plt.scatter(df['{cols[0]}'], df['{cols[1]}')")
            code_parts.append(f"plt.xlabel('{cols[0]}')")
            code_parts.append(f"plt.ylabel('{cols[1]}')")
            code_parts.append(f"plt.title('Scatter: {cols[0]} vs {cols[1]}')")

        elif plot_type == "bar":
            if cols and len(cols) >= 1:
                code_parts.append(f"df['{cols[0]}'].value_counts().plot(kind='bar', figsize=(10, 6))")
                code_parts.append(f"plt.title('Bar chart of {cols[0]}')")
                code_parts.append("plt.xticks(rotation=45)")

        elif plot_type == "box":
            code_parts.append("numeric_df = df.select_dtypes(include=[np.number])")
            if cols:
                code_parts.append(f"cols_to_plot = [c for c in {cols} if c in numeric_df.columns]")
                code_parts.append("if cols_to_plot:")
                code_parts.append("    numeric_df[cols_to_plot].plot(kind='box', figsize=(10, 6))")
            else:
                code_parts.append("numeric_df.plot(kind='box', figsize=(10, 6))")
            code_parts.append("plt.title('Box Plot')")
            code_parts.append("plt.xticks(rotation=45)")

    elif analysis_type == "custom" and custom_code:
        code_parts.append("# Custom analysis")
        code_parts.append(custom_code)

    # Join code and execute
    full_code = "\n".join(code_parts)

    result = await asyncio.to_thread(execute_python, code=full_code, timeout=30)

    return json_dumps(result)

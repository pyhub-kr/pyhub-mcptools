"""Test script for Python sandbox."""

import json

from pyhub.mcptools.python.sandbox_subprocess import execute_python


def test_basic_execution():
    """Test basic Python execution."""
    result = execute_python("print('Hello, World!')")
    print("Basic execution:", json.dumps(result, indent=2))


def test_data_analysis():
    """Test pandas data analysis."""
    code = """
import pandas as pd
import numpy as np

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    'age': [25, 30, 35, 40, 28],
    'score': [85, 92, 78, 88, 95],
    'department': ['Sales', 'IT', 'Sales', 'HR', 'IT']
}

df = pd.DataFrame(data)
print("Dataset:")
print(df)
print("\nBasic Statistics:")
print(df.describe())
print("\nGroup by Department:")
print(df.groupby('department')['score'].mean())
"""
    result = execute_python(code)
    print("\nData analysis:", json.dumps(result, indent=2))


def test_visualization():
    """Test matplotlib visualization."""
    code = """
import matplotlib.pyplot as plt
import numpy as np

# Create data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y1, 'b-', label='sin(x)', linewidth=2)
plt.plot(x, y2, 'r--', label='cos(x)', linewidth=2)
plt.xlabel('x')
plt.ylabel('y')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True, alpha=0.3)
plt.axhline(y=0, color='k', linewidth=0.5)
plt.axvline(x=0, color='k', linewidth=0.5)
"""
    result = execute_python(code)
    print("\nVisualization result keys:", list(result.keys()))
    if "image" in result:
        print("Image generated successfully (base64 length:", len(result["image"]), ")")


def test_security():
    """Test security restrictions."""
    # Test dangerous import
    result = execute_python("import os")
    print("\nTrying to import os:", json.dumps(result, indent=2))

    # Test file access
    result = execute_python("open('/etc/passwd', 'r')")
    print("\nTrying to open file:", json.dumps(result, indent=2))

    # Test eval
    result = execute_python("eval('2+2')")
    print("\nTrying to use eval:", json.dumps(result, indent=2))


def test_timeout():
    """Test execution timeout."""
    code = """
import time
while True:
    pass
"""
    print("\nTesting timeout (this should take ~5 seconds)...")
    result = execute_python(code, timeout=5)
    print("Timeout result:", json.dumps(result, indent=2))


def test_complex_analysis():
    """Test complex data analysis with visualization."""
    code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Generate sample data
np.random.seed(42)
n_samples = 100

data = {
    'x': np.random.normal(100, 15, n_samples),
    'y': np.random.normal(60, 10, n_samples),
    'category': np.random.choice(['A', 'B', 'C'], n_samples),
    'value': np.random.exponential(scale=20, size=n_samples)
}

df = pd.DataFrame(data)

# Create subplots
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('Data Analysis Dashboard', fontsize=16)

# 1. Scatter plot
ax1 = axes[0, 0]
for cat in df['category'].unique():
    mask = df['category'] == cat
    ax1.scatter(df[mask]['x'], df[mask]['y'], label=cat, alpha=0.6)
ax1.set_xlabel('X values')
ax1.set_ylabel('Y values')
ax1.set_title('Scatter Plot by Category')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Histogram
ax2 = axes[0, 1]
df['value'].hist(bins=20, ax=ax2, color='skyblue', edgecolor='black')
ax2.set_xlabel('Value')
ax2.set_ylabel('Frequency')
ax2.set_title('Distribution of Values')

# 3. Box plot
ax3 = axes[1, 0]
df.boxplot(column='value', by='category', ax=ax3)
ax3.set_xlabel('Category')
ax3.set_ylabel('Value')
ax3.set_title('Values by Category')

# 4. Bar plot
ax4 = axes[1, 1]
category_means = df.groupby('category')['value'].mean()
category_means.plot(kind='bar', ax=ax4, color=['coral', 'lightgreen', 'lightblue'])
ax4.set_xlabel('Category')
ax4.set_ylabel('Mean Value')
ax4.set_title('Average Value by Category')
ax4.set_xticklabels(ax4.get_xticklabels(), rotation=0)

plt.tight_layout()

# Print statistics
print("Data Summary:")
print(df.describe())
print("\nValue statistics by category:")
print(df.groupby('category')['value'].agg(['mean', 'std', 'min', 'max']))
"""
    result = execute_python(code, timeout=30)
    print("\nComplex analysis result keys:", list(result.keys()))
    if "output" in result:
        print("Output preview:", result["output"][:200], "...")
    if "image" in result:
        print("Complex visualization generated (base64 length:", len(result["image"]), ")")


if __name__ == "__main__":
    print("Testing Python Sandbox")
    print("=" * 50)

    test_basic_execution()
    print("\n" + "-" * 50)

    test_data_analysis()
    print("\n" + "-" * 50)

    test_visualization()
    print("\n" + "-" * 50)

    test_security()
    print("\n" + "-" * 50)

    test_complex_analysis()
    print("\n" + "-" * 50)

    # Commented out to avoid waiting
    # test_timeout()

# Python Session Management

The Python tools now support session-based state management, allowing you to maintain variables and state across multiple executions.

## Overview

Session management enables:
- **Persistent Variables**: Variables created in one execution are available in subsequent executions
- **State Isolation**: Each session maintains its own isolated namespace
- **SQLite Backend**: Reliable storage of session data with automatic cleanup
- **Security**: All security restrictions still apply within sessions

## Basic Usage

### Creating a Session

Simply provide a `session_id` parameter to `python_repl`:

```python
# First execution - create variables
await python_repl(
    code="x = 42\ny = 'hello'",
    session_id="my_session"
)

# Second execution - use variables
await python_repl(
    code="print(f'{y}, x = {x}')",
    session_id="my_session"
)
# Output: hello, x = 42
```

### Stateless Execution

Omit the `session_id` for traditional stateless execution:

```python
await python_repl(code="print('Hello')")
# Each call is independent
```

## Session Management Tools

### python_list_variables

List all variables in a session:

```python
result = await python_list_variables(session_id="my_session")
# Returns:
# {
#   "session_id": "my_session",
#   "variable_count": 2,
#   "variables": [
#     {"name": "x", "type": "int", "size_bytes": 28},
#     {"name": "y", "type": "str", "size_bytes": 55}
#   ]
# }
```

### python_list_sessions

View all active sessions:

```python
result = await python_list_sessions()
# Returns:
# {
#   "session_count": 3,
#   "sessions": [
#     {
#       "session_id": "my_session",
#       "created_at": "2024-01-10T10:30:00",
#       "variable_count": 5,
#       "total_executions": 12
#     },
#     ...
#   ]
# }
```

### python_clear_session

Remove all variables from a session (session remains active):

```python
await python_clear_session(session_id="my_session")
```

### python_delete_session

Permanently delete a session:

```python
await python_delete_session(session_id="my_session")
```

## Use Cases

### Data Analysis Workflow

```python
# Load and prepare data
await python_repl(
    code="""
import pandas as pd
df = pd.read_csv('data.csv')
df_clean = df.dropna()
""",
    session_id="analysis"
)

# Analyze data
await python_repl(
    code="""
summary = df_clean.describe()
print(summary)
""",
    session_id="analysis"
)

# Create visualizations
await python_repl(
    code="""
import matplotlib.pyplot as plt
df_clean['price'].hist()
plt.title('Price Distribution')
""",
    session_id="analysis"
)
```

### Interactive Development

```python
# Build a model iteratively
await python_repl(
    code="""
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y)
""",
    session_id="ml_dev"
)

# Train model
await python_repl(
    code="""
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)
""",
    session_id="ml_dev"
)

# Evaluate
await python_repl(
    code="""
score = model.score(X_test, y_test)
print(f'R² score: {score}')
""",
    session_id="ml_dev"
)
```

## Technical Details

### Storage

- Sessions are stored in SQLite at `~/.local/share/pyhub.mcptools/python_sessions.db`
- Variables are serialized using pickle
- Maximum 10MB per variable
- Maximum 100MB per session

### Cleanup Policy

- Sessions inactive for 7 days are marked inactive
- Sessions inactive for 30 days are deleted
- Manual cleanup available via `python_delete_session`

### Security

- All sandbox restrictions still apply
- No access to filesystem, network, or system calls
- Sessions are isolated from each other
- Dangerous objects cannot be pickled

### Limitations

- Cannot persist:
  - File handles
  - Network connections
  - Lambda functions
  - Some C extension objects
- Large objects (>10MB) are not saved
- Module imports must be re-executed each session

## Best Practices

1. **Use meaningful session IDs**: Choose descriptive names like "data_analysis_2024"
2. **Clean up sessions**: Delete sessions when done to free resources
3. **Import modules each time**: Sessions don't persist imports
4. **Handle errors gracefully**: Check for NameError when using session variables
5. **Monitor session size**: Use `python_list_variables` to track memory usage

## Example: Complete Workflow

```python
# 1. Start a new analysis session
session_id = "customer_analysis"

# 2. Load and explore data
await python_repl(
    code="""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load customer data
customers = pd.DataFrame({
    'id': range(1000),
    'age': np.random.normal(35, 10, 1000),
    'spending': np.random.exponential(100, 1000)
})

print(f"Loaded {len(customers)} customers")
print(customers.head())
""",
    session_id=session_id
)

# 3. Analyze patterns
await python_repl(
    code="""
# Age groups
customers['age_group'] = pd.cut(customers['age'],
                                bins=[0, 25, 35, 45, 55, 100],
                                labels=['<25', '25-35', '35-45', '45-55', '55+'])

# Spending by age group
spending_by_age = customers.groupby('age_group')['spending'].agg(['mean', 'sum', 'count'])
print(spending_by_age)
""",
    session_id=session_id
)

# 4. Visualize results
await python_repl(
    code="""
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Spending distribution
ax1.hist(customers['spending'], bins=50, alpha=0.7)
ax1.set_xlabel('Spending')
ax1.set_ylabel('Count')
ax1.set_title('Customer Spending Distribution')

# Average spending by age group
spending_by_age['mean'].plot(kind='bar', ax=ax2)
ax2.set_xlabel('Age Group')
ax2.set_ylabel('Average Spending')
ax2.set_title('Average Spending by Age Group')

plt.tight_layout()
""",
    session_id=session_id
)

# 5. Check session status
variables = await python_list_variables(session_id=session_id)
print(f"Session has {variables['variable_count']} variables")

# 6. Clean up when done
await python_delete_session(session_id=session_id)
```
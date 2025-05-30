"""Demo script for Python session management."""

import asyncio
import json
from pyhub.mcptools.python.tools import (
    python_repl,
    python_list_variables,
    python_list_sessions,
    python_clear_session,
)


async def main():
    """Demonstrate Python session functionality."""
    print("=== Python Session Management Demo ===\n")

    # 1. Basic session usage
    print("1. Creating a session and storing variables:")
    session_id = "demo_session"

    result = await python_repl(
        code="""
# Create some data
import pandas as pd
import numpy as np

# Create a DataFrame
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, 30, 35, 28],
    'score': [85, 92, 78, 95]
})

# Calculate statistics
mean_age = df['age'].mean()
mean_score = df['score'].mean()

print("Data created successfully!")
print(f"Average age: {mean_age}")
print(f"Average score: {mean_score}")
""",
        session_id=session_id
    )

    data = json.loads(result)
    print(f"Output:\n{data['output']}")
    print(f"Session ID: {data['session_id']}\n")

    # 2. Using variables from previous execution
    print("2. Using variables from the session:")
    result = await python_repl(
        code="""
# Use the DataFrame from previous execution
print("Top scorers:")
print(df[df['score'] > 85][['name', 'score']])

# Add a new column
df['grade'] = df['score'].apply(lambda x: 'A' if x >= 90 else 'B' if x >= 80 else 'C')
print("\\nUpdated DataFrame:")
print(df)
""",
        session_id=session_id
    )

    data = json.loads(result)
    print(f"Output:\n{data['output']}\n")

    # 3. List variables in session
    print("3. Listing session variables:")
    result = await python_list_variables(session_id=session_id)
    data = json.loads(result)

    print(f"Session has {data['variable_count']} variables:")
    for var in data['variables']:
        print(f"  - {var['name']} ({var['type']}): {var['size_bytes']} bytes")
    print()

    # 4. Create visualization
    print("4. Creating a visualization:")
    result = await python_repl(
        code="""
import matplotlib.pyplot as plt

# Create a bar chart
plt.figure(figsize=(10, 6))
plt.bar(df['name'], df['score'])
plt.xlabel('Student')
plt.ylabel('Score')
plt.title('Student Scores')
plt.ylim(0, 100)

# Add value labels on bars
for i, (name, score) in enumerate(zip(df['name'], df['score'])):
    plt.text(i, score + 1, str(score), ha='center')

plt.tight_layout()
""",
        session_id=session_id
    )

    data = json.loads(result)
    if data.get('image'):
        print("Visualization created successfully (base64 image available)")
    print()

    # 5. Multiple sessions
    print("5. Working with multiple sessions:")

    # Create another session
    await python_repl(
        code="x = 100\ny = 200\nprint(f'Session 2: x={x}, y={y}')",
        session_id="demo_session_2"
    )

    # List all sessions
    result = await python_list_sessions()
    data = json.loads(result)

    print(f"Active sessions: {data['session_count']}")
    for session in data['sessions']:
        print(f"  - {session['session_id']}: "
              f"{session['variable_count']} vars, "
              f"{session['total_executions']} executions")
    print()

    # 6. Session persistence
    print("6. Session persistence across calls:")
    result = await python_repl(
        code="""
# Variables are still available
print(f"DataFrame shape: {df.shape}")
print(f"Mean age (from earlier): {mean_age}")
print(f"Students with grade A: {list(df[df['grade'] == 'A']['name'].values)}")
""",
        session_id=session_id
    )

    data = json.loads(result)
    print(f"Output:\n{data['output']}\n")

    # 7. Clear session
    print("7. Clearing a session:")
    result = await python_clear_session(session_id="demo_session_2")
    data = json.loads(result)
    print(f"Status: {data['status']}")
    print(f"Message: {data['message']}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
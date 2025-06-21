# Excel COM Interface

This module provides direct Windows COM interface for Excel operations, replacing the xlwings dependency.

## Overview

The COM interface provides the same functionality as xlwings but with:
- Direct control over Excel through Windows COM
- Reduced build size (no xlwings dependency)
- Better performance for certain operations
- More explicit resource management

## Architecture

```
com/
├── excel.py      # Core COM wrapper classes (ExcelApp, Workbook, Sheet, Range)
├── utils.py      # Utility functions matching xlwings interface
├── compat.py     # Compatibility layer for switching between implementations
└── README.md     # This file
```

## Usage

### Environment Variable Control

The implementation can be switched using an environment variable:

```python
# Use COM implementation
os.environ['EXCEL_USE_COM'] = 'true'

# Use xlwings implementation (default)
os.environ['EXCEL_USE_COM'] = 'false'
```

### Basic Operations

```python
from pyhub.mcptools.microsoft.excel.com.excel import ExcelApp

# Create Excel application
app = ExcelApp(visible=True)

# Get active workbook or create new one
if app.active_book:
    wb = app.active_book
else:
    wb = app.books.add()

# Work with sheets
sheet = wb.sheets.active
sheet.range("A1").value = "Hello, COM!"

# Set multiple values
data = [["Name", "Age"], ["John", 30], ["Jane", 25]]
sheet.range("A1").value = data

# Clean up
app.quit()
```

### Compatibility Layer

The `compat.py` module provides a unified interface:

```python
from pyhub.mcptools.microsoft.excel.com.compat import (
    get_sheet,
    get_range,
    cleanup_excel_com
)

# These functions work the same regardless of implementation
sheet = get_sheet(book_name="MyWorkbook", sheet_name="Sheet1")
range_obj = get_range("A1:C10", expand_mode="table")
cleanup_excel_com()
```

## Key Differences from xlwings

1. **Explicit COM initialization**: COM is initialized per thread
2. **Index differences**: COM uses 1-based indexing, converted to 0-based in wrapper
3. **Resource cleanup**: More explicit cleanup required with `cleanup_com()`
4. **Windows-only**: This implementation only works on Windows

## Testing

Run compatibility tests to ensure behavior matches xlwings:

```bash
# Run with COM implementation
export EXCEL_USE_COM=true
pytest pyhub/mcptools/microsoft/excel/tests/test_com_compatibility.py

# Run with xlwings implementation
export EXCEL_USE_COM=false
pytest pyhub/mcptools/microsoft/excel/tests/test_excel_integration.py
```

## Migration Guide

To migrate from xlwings:

1. Replace imports:
   ```python
   # Old
   import xlwings as xw

   # New
   from pyhub.mcptools.microsoft.excel.com.compat import (
       App, Workbook, Sheet, Range
   )
   ```

2. Add cleanup calls:
   ```python
   # Add at the end of operations
   cleanup_excel_com()
   ```

3. Handle exceptions:
   ```python
   # Old
   try:
       # xlwings operations
   except Exception as e:
       # handle

   # New
   try:
       # COM operations
   except ExcelError as e:
       # handle
   finally:
       cleanup_excel_com()
   ```

## Performance Considerations

- COM operations are generally faster for bulk data operations
- Connection overhead is similar to xlwings
- Memory usage is more predictable with explicit cleanup
- Parallel operations require careful COM threading management

## Future Enhancements

- [ ] Add more Excel features (charts, pivot tables, etc.)
- [ ] Implement connection pooling for better performance
- [ ] Add async/await support for long operations
- [ ] Create compatibility shim for macOS (AppleScript backend)
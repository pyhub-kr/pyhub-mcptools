# Excel COM Interface Requirements

## System Requirements

### Operating System
- **Windows**: Windows 10/11 (64-bit recommended)
- **Not supported**: macOS, Linux

### Software Requirements
- **Microsoft Excel**:
  - Excel 2016 or later (Excel 365 recommended)
  - Must be properly installed and activated
  - Both 32-bit and 64-bit versions are supported

### Python Requirements
- **Python**: 3.11 or later
- **Architecture**: Must match Excel architecture (32-bit Python for 32-bit Excel)
- **Dependencies**:
  - `pywin32` (automatically installed)
  - Windows COM support

## Environment Detection

The COM interface automatically detects the environment and will:
1. Skip tests if Excel is not installed
2. Fall back to xlwings if COM initialization fails
3. Provide clear error messages for missing requirements

## Testing Environments

### Local Development (Windows with Excel)
```bash
# Full test suite will run
pytest pyhub/mcptools/microsoft/excel/tests/
```

### CI/CD Environments (GitHub Actions)
- Tests requiring Excel will be automatically skipped
- Mock-based tests will still run
- No Excel installation required

### Docker/Container Environments
- COM interface will not be available
- Use xlwings or mock implementations

## Troubleshooting

### Common Issues

1. **"Excel.Application" not found**
   - Ensure Excel is installed
   - Check if Excel is properly registered in Windows registry
   - Try repairing Office installation

2. **COM initialization fails**
   - Check Windows Event Viewer for COM errors
   - Ensure no antivirus is blocking COM access
   - Try running as administrator

3. **32-bit vs 64-bit mismatch**
   - Check Excel version: File → Account → About Excel
   - Install matching Python architecture
   - Use `python -c "import sys; print(sys.version)"` to check Python architecture

### Verification Script

```python
# Check if Excel COM is available
import sys
if sys.platform == "win32":
    try:
        import win32com.client
        excel = win32com.client.Dispatch("Excel.Application")
        print(f"Excel COM available: {excel.Version}")
        excel.Quit()
    except Exception as e:
        print(f"Excel COM not available: {e}")
else:
    print("Not on Windows")
```
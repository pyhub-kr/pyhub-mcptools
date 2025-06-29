"""Excel-specific exceptions for better error handling."""


class ExcelError(Exception):
    """Base exception for all Excel-related errors."""

    pass


class WorkbookNotFoundError(ExcelError):
    """Raised when a workbook cannot be found."""

    def __init__(self, workbook_name: str):
        super().__init__(
            f"Workbook '{workbook_name}' not found. " f"Please check the name and ensure the file is open."
        )
        self.workbook_name = workbook_name


class SheetNotFoundError(ExcelError):
    """Raised when a sheet cannot be found."""

    def __init__(self, sheet_name: str, workbook_name: str = None):
        if workbook_name:
            message = f"Sheet '{sheet_name}' not found in workbook '{workbook_name}'."
        else:
            message = f"Sheet '{sheet_name}' not found in active workbook."
        super().__init__(message)
        self.sheet_name = sheet_name
        self.workbook_name = workbook_name


class RangeError(ExcelError):
    """Raised when there's an issue with an Excel range."""

    def __init__(self, range_address: str, reason: str = None):
        message = f"Invalid range '{range_address}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.range_address = range_address
        self.reason = reason


class ExcelNotInstalledError(ExcelError):
    """Raised when Excel is not installed or available."""

    def __init__(self):
        super().__init__(
            "Microsoft Excel is not installed or not available. " "Please ensure Excel is installed and accessible."
        )


class ExcelCOMError(ExcelError):
    """Raised when Excel COM automation fails."""

    def __init__(self, operation: str, detail: str = None):
        message = f"Excel COM operation '{operation}' failed"
        if detail:
            message += f": {detail}"
        super().__init__(message)
        self.operation = operation
        self.detail = detail


class ExcelPermissionError(ExcelError):
    """Raised when Excel operations require permissions (macOS)."""

    def __init__(self):
        super().__init__(
            "Excel automation requires permission. "
            "Please grant access when prompted or check System Preferences > "
            "Security & Privacy > Privacy > Automation."
        )


class DataValidationError(ExcelError):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: any, expected: str):
        super().__init__(f"Invalid value for '{field}': {value}. Expected: {expected}")
        self.field = field
        self.value = value
        self.expected = expected

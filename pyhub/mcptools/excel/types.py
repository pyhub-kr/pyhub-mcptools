from typing import Annotated

from pydantic import BeforeValidator, Field

from pyhub.mcptools.excel.validators import validate_excel_range, validate_formula

ExcelFormula = Annotated[
    str,
    BeforeValidator(validate_formula),
    Field(
        description="Excel Formula (must start with '=' and follow Excel formula patterns: "
        "cell references, functions, operations, literals)"
    ),
]


ExcelRange = Annotated[
    str,
    BeforeValidator(validate_excel_range),
    Field(description="Excel Range (ex: 'A1', 'A1:C3', 'Sheet1!A1', '$A$1:$C$3')"),
]

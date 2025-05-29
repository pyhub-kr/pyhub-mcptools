"""PyInstaller 빌드 시 경고 억제 및 설정"""
import warnings
import sys

# pkg_resources 경고 억제
warnings.filterwarnings("ignore", category=UserWarning, module="altgraph")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# Pydantic JSON Schema 경고 억제
try:
    from pydantic.json_schema import PydanticJsonSchemaWarning
    warnings.filterwarnings("ignore", category=PydanticJsonSchemaWarning)
except ImportError:
    pass
from abc import abstractmethod
from typing import Any, Generic, TypeVar

from django.db.models import IntegerChoices, TextChoices
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

T = TypeVar("T", str, int)

NOT_SPECIFIED = object()


class ChoicesMixin(Generic[T]):
    @classmethod
    def get_attr_value(cls, name: str) -> T:
        return getattr(cls, name).value

    @classmethod
    @abstractmethod
    def get_none_value(cls):
        return NOT_SPECIFIED

    @classmethod
    def get_description(cls, prefix: str = "") -> str:
        choices = {el.value: (el.label or el.name) for el in cls}
        none_value = cls.get_none_value()

        if none_value is not NOT_SPECIFIED:
            guide = f"Use '{none_value}' for no change"
        else:
            guide = ""

        return f"""{prefix}

choices: {choices}

{guide}""".strip()


class PyHubTextChoices(ChoicesMixin[str], TextChoices):
    @classmethod
    def get_none_value(cls) -> str:
        return ""


class PyHubIntegerChoices(ChoicesMixin[int], IntegerChoices):
    @classmethod
    def get_none_value(cls) -> int:
        return 0


class StringBool(str):
    ENUM = ("", "f", "t")
    # 값 판단은 enum보다 넓은 범위로 지정
    TRUE_VALUES = ("1", "t", "y", "T", "Y")

    def __bool__(self) -> bool:
        return self[0] in self.TRUE_VALUES

    def is_specified(self) -> bool:
        """값이 지정된 것인지 여부"""
        return len(self) > 0

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler: GetCoreSchemaHandler):
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        return cls(value)


# json_schema 지원을 위해 아래 메서드를 등록
def stringbool_json_schema(schema: Any, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
    return {
        "type": "string",
        "enum": StringBool.ENUM,
    }


StringBool.__get_pydantic_json_schema__ = stringbool_json_schema

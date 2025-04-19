from typing import Callable, TypeVar

from django import forms

T = TypeVar("T")


class BaseCommaSeperatedField(forms.CharField):
    """쉼표로 구분된 문자열을 리스트로 변환하는 기본 필드"""

    def __init__(
        self, *args, converter: Callable[[str], T], error_message: str, separator: str = ",", **kwargs
    ) -> None:
        """
        Args:
            converter: 각 항목을 변환하는 함수
            error_message: 변환 실패시 표시할 에러 메시지
            separator: 구분자 (기본값: ",")
            *args, **kwargs: CharField의 다른 인자들
        """
        super().__init__(*args, **kwargs)
        self.converter = converter
        self.error_message = error_message
        self.separator = separator

    def to_python(self, value: str | None) -> list[T]:
        """구분자로 나눈 문자열을 지정된 타입의 리스트로 변환합니다.

        Args:
            value: 구분자로 나눈 문자열

        Returns:
            list[T]: 변환된 리스트

        Raises:
            forms.ValidationError: 값을 지정된 타입으로 변환할 수 없는 경우
        """
        if not value:
            return []

        items = [item.strip() for item in str(value).split(self.separator) if item.strip()]
        converted = []

        for item in items:
            try:
                converted.append(self.converter(item))
            except (ValueError, TypeError) as e:
                raise forms.ValidationError(self.error_message.format(value=item)) from e

        return converted


class CommaSeperatedField(BaseCommaSeperatedField):
    """쉼표로 구분된 문자열을 문자열 리스트로 변환하는 필드"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args,
            converter=str,
            error_message="'{value}'은(는) 문자열로 변환할 수 없습니다.",
            **kwargs,
        )


class IntegerCommaSeperatedField(BaseCommaSeperatedField):
    """쉼표로 구분된 문자열을 정수 리스트로 변환하는 필드"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args,
            converter=int,
            error_message="'{value}'은(는) 정수로 변환할 수 없습니다.",
            **kwargs,
        )


class FloatCommaSeperatedField(BaseCommaSeperatedField):
    """쉼표로 구분된 문자열을 실수 리스트로 변환하는 필드"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args,
            converter=float,
            error_message="'{value}'은(는) 실수로 변환할 수 없습니다.",
            **kwargs,
        )

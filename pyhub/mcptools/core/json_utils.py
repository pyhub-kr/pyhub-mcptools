"""JSON utilities for MCP tools."""

import json
import base64
from datetime import datetime, date
from typing import Any, Optional, Dict, Literal, Union, Collection
from dataclasses import is_dataclass, asdict


EmptyValueType = Literal["none", "empty_str", "empty_list", "empty_dict", "all"]
EmptyValueTypes = Union[EmptyValueType, Collection[EmptyValueType]]


class JSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self.use_base64 = kwargs.pop("use_base64", False)
        self.skip_empty = kwargs.pop("skip_empty", None)
        super().__init__(*args, **kwargs)

    def _is_empty(self, value: Any) -> bool:
        if self.skip_empty is None:
            return False

        # skip_empty가 문자열인 경우 (단일 옵션)
        if isinstance(self.skip_empty, str):
            if self.skip_empty == "all":
                return value is None or value == "" or value == [] or value == {}
            return (
                (self.skip_empty == "none" and value is None)
                or (self.skip_empty == "empty_str" and value == "")
                or (self.skip_empty == "empty_list" and value == [])
                or (self.skip_empty == "empty_dict" and value == {})
            )

        # skip_empty가 컬렉션인 경우 (다중 옵션)
        return (
            ("none" in self.skip_empty and value is None)
            or ("empty_str" in self.skip_empty and value == "")
            or ("empty_list" in self.skip_empty and value == [])
            or ("empty_dict" in self.skip_empty and value == {})
        )

    def _filter_empty(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        if not self.skip_empty:
            return obj
        return {k: v for k, v in obj.items() if not self._is_empty(v)}

    def default(self, o):
        if is_dataclass(o):
            return self._filter_empty(asdict(o))
        elif isinstance(o, (datetime, date)):
            return o.isoformat()
        elif isinstance(o, bytes):
            if self.use_base64:
                return base64.b64encode(o).decode("ascii")
            return o.decode("utf-8")
        elif isinstance(o, memoryview):
            if self.use_base64:
                return base64.b64encode(o.tobytes()).decode("ascii")
            return o.tobytes().decode("utf-8")
        elif isinstance(o, (set, frozenset)):
            return list(o)
        elif isinstance(o, dict):
            return self._filter_empty(o)
        return super().default(o)


def json_dumps(
    json_data: Any,
    use_base64: bool = False,
    skip_empty: Optional[EmptyValueTypes] = None,
    indent: int = 2,
) -> str:
    return json.dumps(
        json_data,
        ensure_ascii=False,
        cls=JSONEncoder,
        use_base64=use_base64,
        skip_empty=skip_empty,
        indent=indent,
    )

import json
import base64
from datetime import datetime, date
from typing import Any, Optional, Dict, Literal, Union, Collection

import psutil
from dataclasses import is_dataclass, asdict
import html2text


EmptyValueType = Literal["none", "empty_str", "empty_list", "empty_dict", "all"]
EmptyValueTypes = Union[EmptyValueType, Collection[EmptyValueType]]


def is_outlook_64bit() -> Optional[bool]:
    processes = check_outlook_process()
    if not processes:
        return None

    for process in processes:
        if process["is_64bit"]:
            return True
    return False


def check_outlook_process() -> list[dict[str, Any]]:
    outlook_processes = []

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if "OUTLOOK.EXE" in proc.info["name"].upper():
                exe_path = proc.info["exe"]
                if exe_path:
                    # 실행 파일의 크기로 32비트/64비트 판단
                    with open(exe_path, "rb") as f:
                        # PE 헤더의 Machine 필드 확인
                        f.seek(60)  # PE 헤더 오프셋
                        pe_header_offset = int.from_bytes(f.read(4), "little")
                        f.seek(pe_header_offset + 4)  # Machine 필드
                        machine = int.from_bytes(f.read(2), "little")

                        is_64bit = machine == 0x8664  # x64

                        outlook_processes.append({"pid": proc.info["pid"], "path": exe_path, "is_64bit": is_64bit})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return outlook_processes


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


def html_to_text(html: str) -> str:
    """
    Convert HTML to Markdown text using html2text.
    """
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Disable line wrapping
    return h.handle(html)

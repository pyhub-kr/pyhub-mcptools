from typing import Annotated, Union

from pydantic import BeforeValidator, Field

from pyhub.mcptools.core.types import PyHubTextChoices
from pyhub.mcptools.music.utils import remove_quotes


class MusicServiceVendor(PyHubTextChoices):
    MELON = "melon"


# LLM을 통한 인자에서 쌍따옴표/홑따옴표가 붙기도 합니다. 이를 제거하지 않으면 멜론에서 검색결과가 없습니다.
SongUid = Annotated[
    Union[str],
    BeforeValidator(remove_quotes),
    Field(description="Song unique identifier that can be either an integer or string"),
]

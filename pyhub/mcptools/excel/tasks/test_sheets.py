import json
from os import getenv

import pytest

from pyhub.mcptools.excel.tasks import sheets as sheets_tasks

# 파일 내 모든 테스트에 적용될 마커
pytestmark = pytest.mark.skipif(not getenv("PYCHARM_HOSTED"), reason="These tests only run in PyCharm GUI")


def test_get_opened_workbooks():
    ret = sheets_tasks.get_opened_workbooks()
    assert isinstance(ret, str)
    assert isinstance(json.loads(ret), dict)


@pytest.mark.parametrize(
    "styles",
    [
        """book_name|sheet_name|sheet_range|expand_mode|background_color|font_color|bold|italic
|A2:B2||255,230,230|0,0,0|false|false
|A3:B3||230,242,255|0,0,0|false|false
|A4:B4||255,250,230|0,0,0|false|false
|A5:B5||230,255,230|0,0,0|false|false
|A6:B6||230,242,255|0,0,0|false|false
|A7:B7||230,242,255|0,0,0|false|false
|A8:B8||255,230,240|0,0,0|false|false
|A9:B9||255,250,230|0,0,0|false|false
|A10:B10||255,250,230|0,0,0|false|false
|A11:B11||230,255,230|0,0,0|false|false""",
        "A1:B2;background_color=255,255,0;bold=true",
        "Sheet1!A1:C5;font_color=255,0,0;italic=true",
        """book_name|sheet_name|sheet_range|expand_mode|background_color|font_color|bold|italic
|Sheet1|A1:B2||255,255,0|255,0,0|true|false""",
    ],
)
def test_set_styles(styles):
    ret = sheets_tasks.set_styles(styles)
    print(ret)

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


def test_set_styles():
    styles = """range|background_color|font_color
A1|255,200,200|0,0,0
A2|255,200,200|0,0,0
A5|255,200,200|0,0,0
A6|255,200,200|0,0,0
A8|255,200,200|0,0,0
A9|255,200,200|0,0,0
A3|200,255,200|0,0,128
A4|180,180,255|255,255,255
A7|180,180,255|255,255,255
A10|180,180,255|255,255,255"""
    ret = sheets_tasks.set_styles(styles)
    print(ret)

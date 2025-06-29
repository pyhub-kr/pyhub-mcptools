"""Google Sheets 테스트 설정"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import Mock

import pytest

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Django 설정
def pytest_configure():
    """pytest 실행 시 Django 설정"""
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            USE_GOOGLE_SHEETS=True,
            GOOGLE_CLIENT_SECRET_PATH=os.getenv("GOOGLE_CLIENT_SECRET_PATH", "./google_client_secret.json"),
            SECRET_KEY="test-secret-key-for-pytest",
            DEBUG=True,
            ONLY_EXPOSE_TOOLS=None,  # MCP 도구 필터링 비활성화
            EXPERIMENTAL=False,  # 실험적 기능 비활성화
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
        )
        django.setup()


@pytest.fixture(scope="session")
def event_loop():
    """진정한 세션 스코프 이벤트 루프 강제 구현"""

    # 새로운 이벤트 루프 생성
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()

    # 이벤트 루프를 현재 스레드의 기본 루프로 설정
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        # 정리 작업
        try:
            # 남은 태스크들 정리
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


@pytest.fixture(scope="session")
def google_sheets_enabled():
    """Google Sheets가 활성화되어 있는지 확인"""
    if not os.getenv("USE_GOOGLE_SHEETS"):
        pytest.skip("USE_GOOGLE_SHEETS environment variable not set")
    if not os.getenv("GOOGLE_CLIENT_SECRET_PATH"):
        pytest.skip("GOOGLE_CLIENT_SECRET_PATH environment variable not set")
    return True


@pytest.fixture(scope="session")
async def test_spreadsheet_id(google_sheets_enabled):
    """테스트용 스프레드시트 생성 및 정리"""
    import json

    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_create_spreadsheet

    # 테스트 스프레드시트 생성
    test_name = f"pytest-test-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result = await gsheet_create_spreadsheet(name=test_name)
    data = json.loads(result)
    spreadsheet_id = data["id"]

    yield spreadsheet_id

    # 정리는 사용자가 수동으로 진행 (Google Drive에서 삭제)
    print(f"\nTest spreadsheet created: {test_name}")
    print(f"ID: {spreadsheet_id}")
    print("Please delete it manually from Google Drive if needed.")


@pytest.fixture
async def sheet_info(test_spreadsheet_id):
    """테스트 스프레드시트의 첫 번째 시트 정보"""
    import json

    from pyhub.mcptools.google.sheets.tools.sheets import gsheet_get_spreadsheet_info

    result = await gsheet_get_spreadsheet_info(spreadsheet_id=test_spreadsheet_id)
    data = json.loads(result)
    return data["sheets"][0]


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    return [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "London"],
        ["Charlie", "35", "Tokyo"],
    ]


@pytest.fixture
def sample_csv_data():
    """테스트용 CSV 데이터"""
    return "Product,Price,Stock\nLaptop,999,10\nMouse,29,50\nKeyboard,79,30"


@pytest.fixture
def mock_google_sheets_client():
    """Google Sheets 클라이언트 모킹"""
    mock_client = Mock()
    return mock_client


@pytest.fixture
def mock_credentials():
    """Google 인증 정보 모킹"""
    mock_creds = Mock()
    mock_creds.valid = True
    return mock_creds


# pytest 마커는 pytest.ini에서 정의됨

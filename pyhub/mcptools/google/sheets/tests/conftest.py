"""Google Sheets 테스트 설정"""

import pytest
from unittest.mock import Mock


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
"""데스크톱 애플리케이션용 Google Sheets 인증 헬퍼

배포용 데스크톱 앱에서 OAuth 크레덴셜을 관리하는 예시입니다.
실제 배포 시에는 이 파일을 참고하여 구현하세요.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DesktopAuthManager:
    """데스크톱 앱용 인증 관리자"""

    def __init__(self, app_name: str = "pyhub-mcptools"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_dir(self) -> Path:
        """OS별 설정 디렉토리 반환"""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", "~"))
        elif os.name == "posix":
            if "darwin" in sys.platform:  # macOS
                base = Path.home() / "Library" / "Application Support"
            else:  # Linux
                base = Path.home() / ".config"
        else:
            base = Path.home()

        return base / self.app_name

    def get_credentials_path(self) -> Optional[Path]:
        """사용 가능한 크레덴셜 경로 반환"""
        # 1. 사용자 커스텀 크레덴셜 확인
        custom_path = self.config_dir / "google_client_secret.json"
        if custom_path.exists():
            logger.info("사용자 크레덴셜 사용")
            return custom_path

        # 2. 번들된 기본 크레덴셜 확인 (배포 시 포함)
        bundled_path = Path(__file__).parent / "data" / "default_client_secret.json"
        if bundled_path.exists():
            logger.info("공용 크레덴셜 사용 (API 제한 있음)")
            return bundled_path

        return None

    def save_user_credentials(self, credentials_json: str) -> Path:
        """사용자 크레덴셜 저장"""
        # JSON 유효성 검증
        try:
            data = json.loads(credentials_json)
            if "installed" not in data and "web" not in data:
                raise ValueError("올바른 OAuth 크레덴셜 형식이 아닙니다")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"크레덴셜 검증 실패: {e}") from e

        # 저장
        custom_path = self.config_dir / "google_client_secret.json"
        custom_path.write_text(credentials_json)
        logger.info(f"사용자 크레덴셜 저장됨: {custom_path}")
        return custom_path

    def get_setup_instructions(self) -> Dict[str, Any]:
        """설정 안내 정보 반환"""
        return {
            "steps": [
                {
                    "title": "Google Cloud Console 접속",
                    "url": "https://console.cloud.google.com/",
                    "description": "Google Cloud Console에 로그인하세요",
                },
                {"title": "프로젝트 생성", "description": "새 프로젝트를 생성하거나 기존 프로젝트를 선택하세요"},
                {
                    "title": "API 활성화",
                    "apis": ["Google Sheets API", "Google Drive API"],
                    "description": "필요한 API를 활성화하세요",
                },
                {
                    "title": "OAuth 클라이언트 생성",
                    "type": "Desktop Application",
                    "description": "데스크톱 애플리케이션 타입으로 OAuth 클라이언트를 생성하세요",
                },
                {"title": "크레덴셜 다운로드", "description": "JSON 파일을 다운로드하여 이 앱에 등록하세요"},
            ],
            "benefits": {
                "custom": ["API 호출 제한 없음", "독립적인 할당량", "자체 프로젝트 관리"],
                "default": ["즉시 사용 가능", "설정 불필요", "API 호출 제한 있음 (분당 60회)"],
            },
        }

    def check_api_limit_status(self) -> Dict[str, Any]:
        """API 제한 상태 확인"""
        is_custom = (self.config_dir / "google_client_secret.json").exists()

        return {
            "type": "custom" if is_custom else "default",
            "limits": {
                "per_minute": None if is_custom else 60,
                "per_day": None if is_custom else 20000,
                "concurrent": None if is_custom else 10,
            },
            "recommendation": None if is_custom else "API 제한을 없애려면 개인 크레덴셜을 설정하세요",
        }


# 사용 예시
if __name__ == "__main__":
    # 데스크톱 앱 초기화 시
    auth_manager = DesktopAuthManager()

    # 크레덴셜 확인
    creds_path = auth_manager.get_credentials_path()
    if not creds_path:
        print("크레덴셜이 없습니다. 설정이 필요합니다.")

        # 설정 안내 표시
        instructions = auth_manager.get_setup_instructions()
        print("\n=== Google Sheets 설정 가이드 ===")
        for i, step in enumerate(instructions["steps"], 1):
            print(f"{i}. {step['title']}: {step['description']}")
    else:
        # API 상태 확인
        status = auth_manager.check_api_limit_status()
        print(f"\n현재 상태: {status['type']} 크레덴셜 사용 중")
        if status["recommendation"]:
            print(f"권장사항: {status['recommendation']}")

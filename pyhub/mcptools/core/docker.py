"""Docker 환경 탐지 유틸리티"""

import os


def is_docker_container() -> bool:
    """Docker 컨테이너 환경인지 탐지합니다.

    Returns:
        bool: Docker 컨테이너 환경이면 True, 아니면 False
    """
    # 방법 1: /.dockerenv 파일 존재 여부 확인
    if os.path.exists("/.dockerenv"):
        return True

    # 방법 2: /proc/1/cgroup 파일에서 docker 문자열 확인 (Linux)
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    # 방법 3: 환경변수 확인 (사용자가 명시적으로 설정한 경우)
    if os.environ.get("DOCKER_CONTAINER", "").lower() in ("1", "true", "yes"):
        return True

    # 방법 4: /proc/self/mountinfo 확인 (Linux)
    try:
        with open("/proc/self/mountinfo", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    return False

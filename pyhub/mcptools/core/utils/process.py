import subprocess
import sys
import time

import psutil

from pyhub.mcptools.core.choices import OS, McpHostChoices


def is_mcp_host_running(mcp_host: McpHostChoices) -> bool:
    """MCP 호스트가 실행 중인지 확인합니다."""
    match OS.get_current():
        case OS.WINDOWS:
            return _is_running_in_windows(mcp_host)
        case OS.MACOS:
            return _is_running_in_macos(mcp_host)
        case _:
            raise ValueError(f"Unsupported platform : {sys.platform}")


def _is_running_in_windows(mcp_host: McpHostChoices) -> bool:
    """Windows에서 MCP 호스트 실행 상태 확인"""
    process_names = []

    if mcp_host == McpHostChoices.CLAUDE:
        process_names = ["claude.exe", "claude helper.exe", "claude helper (gpu).exe", "claude helper (renderer).exe"]
    elif mcp_host == McpHostChoices.CURSOR:
        process_names = ["cursor.exe"]
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host}")

    for proc in psutil.process_iter(["name"]):
        try:
            proc_name = proc.info["name"].lower()
            if any(name.lower() in proc_name for name in process_names):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return False


def _is_running_in_macos(mcp_host: McpHostChoices) -> bool:
    """macOS에서 MCP 호스트 실행 상태 확인"""
    if mcp_host == McpHostChoices.CLAUDE:
        # pgrep으로 Claude.app 프로세스 확인
        result = subprocess.run("pgrep -f '/Applications/Claude.app/'", shell=True, capture_output=True, text=True)
        return result.returncode == 0
    elif mcp_host == McpHostChoices.CURSOR:
        result = subprocess.run("pgrep -f '/Applications/Cursor.app/'", shell=True, capture_output=True, text=True)
        return result.returncode == 0
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host.value}")


def kill_mcp_host_process(mcp_host: McpHostChoices) -> None:
    """MCP 호스트 프로세스를 종료하고 완전히 종료될 때까지 대기합니다."""
    match OS.get_current():
        case OS.WINDOWS:
            kill_in_windows(mcp_host)
        case OS.MACOS:
            kill_in_macos(mcp_host)
        case _:
            raise ValueError(f"Unsupported platform : {sys.platform}")

    # 프로세스가 완전히 종료될 때까지 최대 5초 대기
    for i in range(5):
        if not is_mcp_host_running(mcp_host):
            print(f"{mcp_host} processes completely terminated")
            break
        time.sleep(1)
        print(f"Waiting for {mcp_host} processes to terminate... ({i+1}/5)")
    else:
        print(f"Warning: Some {mcp_host} processes may still be running")


def kill_in_windows(mcp_host: McpHostChoices) -> None:
    def _kill_by_name_pattern(pattern: str) -> int:
        """프로세스 이름 패턴으로 종료하고 종료된 프로세스 수 반환"""
        killed_count = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info["name"].lower()
                if pattern.lower() in proc_name:
                    print(f"Killing: {proc.info['name']} (PID {proc.pid})")
                    proc.terminate()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return killed_count

    total_killed = 0

    if mcp_host == McpHostChoices.CLAUDE:
        # Claude Desktop 관련 모든 프로세스 종료
        process_patterns = [
            "claude.exe",
            "claude helper",  # Claude Helper.exe, Claude Helper (GPU).exe 등 포함
        ]

        for pattern in process_patterns:
            killed = _kill_by_name_pattern(pattern)
            total_killed += killed

        if total_killed > 0:
            print(f"Total {total_killed} Claude processes killed")
        else:
            print("No Claude processes found")

    elif mcp_host == McpHostChoices.CURSOR:
        killed = _kill_by_name_pattern("cursor.exe")
        if killed > 0:
            print(f"Total {killed} Cursor processes killed")
        else:
            print("No Cursor processes found")
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host}")


def kill_in_macos(mcp_host: McpHostChoices) -> None:
    if mcp_host == McpHostChoices.CLAUDE:
        # Claude Desktop GUI 앱 종료
        result = subprocess.run("pkill -f '/Applications/Claude.app/'", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("Claude Desktop processes killed successfully")
        else:
            print("No Claude Desktop processes found to kill")

    elif mcp_host == McpHostChoices.CURSOR:
        result = subprocess.run("pkill -f '/Applications/Cursor.app/'", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("Cursor processes killed successfully")
        else:
            print("No Cursor processes found to kill")
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host.value}")

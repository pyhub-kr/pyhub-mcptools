import subprocess
import sys

import psutil

from pyhub.mcptools.core.types import McpClientEnum


def kill_mcp_client_process(target: McpClientEnum) -> None:
    if sys.platform.startswith("win"):
        kill_in_windows(target)
    elif sys.platform == "darwin":
        kill_in_macos(target)
    else:
        raise ValueError(f"Unsupported platform : {sys.platform}")


def kill_in_windows(target: McpClientEnum) -> None:
    def _kill(proc_name: str) -> None:
        for proc in psutil.process_iter(["pid", "name"]):
            proc_pid = proc.pid
            try:
                if proc.info["name"].lower() == proc_name.lower():
                    print(f"Killing: {proc_name} (PID {proc_pid})")
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if target == McpClientEnum.CLAUDE:
        _kill("claude.exe")
    elif target == McpClientEnum.CURSOR:
        _kill("cursor.exe")
    else:
        raise ValueError(f"Unsupported target : {target}")


def kill_in_macos(target: McpClientEnum) -> None:
    if target == McpClientEnum.CLAUDE:
        subprocess.run("pkill -f '/Applications/Claude.app/'", shell=True)
    elif target == McpClientEnum.CURSOR:
        subprocess.run("pkill -f '/Applications/Cursor.app/'", shell=True)
    else:
        raise ValueError(f"Unsupported target : {target.value}")

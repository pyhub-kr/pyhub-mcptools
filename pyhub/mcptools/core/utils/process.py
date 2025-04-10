import subprocess
import sys

import psutil

from pyhub.mcptools.core.choices import OS, McpHostChoices


def kill_mcp_host_process(mcp_host: McpHostChoices) -> None:
    match OS.get_current():
        case OS.WINDOWS:
            kill_in_windows(mcp_host)
        case OS.MACOS:
            kill_in_macos(mcp_host)
        case _:
            raise ValueError(f"Unsupported platform : {sys.platform}")


def kill_in_windows(mcp_host: McpHostChoices) -> None:
    def _kill(proc_name: str) -> None:
        for proc in psutil.process_iter(["pid", "name"]):
            proc_pid = proc.pid
            try:
                if proc.info["name"].lower() == proc_name.lower():
                    print(f"Killing: {proc_name} (PID {proc_pid})")
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if mcp_host == McpHostChoices.CLAUDE:
        _kill("claude.exe")
    elif mcp_host == McpHostChoices.CURSOR:
        _kill("cursor.exe")
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host}")


def kill_in_macos(mcp_host: McpHostChoices) -> None:
    if mcp_host == McpHostChoices.CLAUDE:
        subprocess.run("pkill -f '/Applications/Claude.app/'", shell=True)
    elif mcp_host == McpHostChoices.CURSOR:
        subprocess.run("pkill -f '/Applications/Cursor.app/'", shell=True)
    else:
        raise ValueError(f"Unsupported MCP Host : {mcp_host.value}")

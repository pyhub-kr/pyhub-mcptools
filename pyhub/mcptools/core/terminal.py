import platform
import shutil
import subprocess
from pathlib import Path
from typing import Union

MACOS_ITERM_SCRIPT = """
    tell application "iTerm"
        create window with default profile
        tell current session of current window
            write text "cd {path}"
        end tell
    end tell
"""

MACOS_TERMINAL_SCRIPT = """
    tell application "Terminal"
        do script "cd {path}"
        activate
    end tell
"""


WINDOWS_BAT_SCRIPT = """
    @echo off
    cd /d %1
    cmd /k
"""


def open_terminal(path: Union[str, Path]) -> None:
    if isinstance(path, str):
        path = Path(path)

    system = platform.system()

    if system == "Darwin":  # macOS
        if shutil.which("osascript"):
            try:
                script = MACOS_ITERM_SCRIPT.format(path=path)
                subprocess.run(["osascript", "-e", script])
                return
            except:  # noqa
                pass

        # Terminal fallback
        script = MACOS_TERMINAL_SCRIPT.format(path=path)
        subprocess.run(["osascript", "-e", script])

    elif system == "Windows":
        bat_path = Path(__file__).parent / "launch.bat"
        bat_path.write_text(WINDOWS_BAT_SCRIPT, encoding="utf-8")
        subprocess.run(["cmd", "/c", bat_path, path])

    else:
        raise NotImplementedError(f"Unsupported system: {system}")

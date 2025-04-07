import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from rich.console import Console
from typer import Exit

console = Console()


def get_config_path(host: str, is_verbose: bool = False) -> Path:
    """현재 운영체제에 맞는 설정 파일 경로를 반환합니다."""
    os_system = sys.platform.lower()
    if os_system.startswith("win"):
        os_system = "windows"

    home = Path.home()

    try:
        path = {
            ("darwin", "claude"): home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            ("windows", "claude"): home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        }[(os_system, host)]
    except KeyError:
        pass
    else:
        if is_verbose:
            console.print(f"[INFO] config path : {path}", highlight=False)
        return path

    raise ValueError(f"{os_system}의 {host} 프로그램은 지원하지 않습니다.")


@contextmanager
def read_config_file(path: Path, is_verbose: bool = False):
    """설정 파일을 읽어서 반환합니다. with 문에서 사용 가능합니다."""
    if not path.exists():
        raise IOError(f"{path} 경로의 파일이 아직 없습니다.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config_data: dict = json.load(f)
            yield config_data
    except json.JSONDecodeError as e:
        raise ValueError("설정 파일이 JSON 포맷이 아닙니다.") from e
    except Exception as e:
        if is_verbose:
            console.print_exception()
        else:
            console.print(f"[red]{type(e).__name__}: {e}[/red]")
        raise Exit(1) from e


def get_editor_commands() -> list[str]:
    """시스템에서 사용 가능한 에디터 명령어 목록을 반환합니다."""

    # 환경 변수에서 기본 에디터 확인
    editors = []

    # VISUAL or EDITOR 환경 변수 확인
    if "VISUAL" in os.environ:
        editors.append(os.environ["VISUAL"])
    if "EDITOR" in os.environ:
        editors.append(os.environ["EDITOR"])

    if sys.platform.startswith("win"):
        editors.extend(["code", "notepad++", "notepad"])
    else:
        editors.extend(["code", "vim", "nano", "emacs", "gedit"])

    return editors


def open_with_default_editor(file_path: Path, is_verbose: bool = False) -> bool:
    """다양한 에디터 명령을 시도하여 파일을 엽니다."""
    file_path_str = str(file_path)

    # 다양한 에디터 명령 시도
    editors = get_editor_commands()
    last_error = None

    for editor in editors:
        try:
            if editor == "code":  # VS Code의 경우 특별 처리
                subprocess.run(["code", "--wait", file_path_str], check=True)
                if is_verbose:
                    console.print("[green]Visual Studio Code 에디터로 파일을 열었습니다.[/green]")
            else:
                subprocess.run([editor, file_path_str], check=True)
                if is_verbose:
                    console.print(f"[green]{editor} 에디터로 파일을 열었습니다.[/green]")
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            last_error = e
            continue

    # 플랫폼 기본 명령 시도
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["start", file_path_str], shell=True, check=True)
            if is_verbose:
                console.print("[green]Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
            return True
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", file_path_str], check=True)
            if is_verbose:
                console.print("[green]macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
            return True
        else:
            subprocess.run(["xdg-open", file_path_str], check=True)
            if is_verbose:
                console.print("[green]Linux 기본 프로그램으로 파일을 열었습니다.[/green]")
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 모든 시도가 실패한 경우
    error_msg = f"파일을 열 수 있는 에디터를 찾을 수 없습니다. 시도한 에디터: {', '.join(editors)}"
    if last_error:
        error_msg += f"\n마지막 오류: {str(last_error)}"
    return False
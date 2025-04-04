import typer
from rich.console import Console
from typer import Argument, Option

from ..core.cli import app
from . import tools  # noqa
from .choices import McpHostChoices
from .utils import get_config_path, open_with_default_editor, read_config_file

console = Console()


@app.command(name="print")
def print_(
    host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """지정 MCP 호스트의 MCP 설정을 출력합니다."""

    try:
        host_value = str(host)
        config_path = get_config_path(host_value)
        if is_verbose:
            console.print(f"Loading config from {config_path}", highlight=False)
        config_data = read_config_file(config_path)
        console.print(config_data)
    except Exception as e:
        if is_verbose:
            console.print_exception()
        else:
            console.print(f"[red]{type(e).__name__}: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def edit(
    host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """가용 에디터로 즉시 MCP 설정 파일 편집"""
    host_value = str(host)
    config_path = get_config_path(host_value)
    if is_verbose:
        console.print(f"config path = {config_path}", highlight=False)
    open_with_default_editor(config_path, is_verbose)


# @app.command()
# def add(
#     host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
#     is_verbose: bool = Option(False, "--verbose", "-v"),
# ):
#     """지정 MCP 설정을 현재 OS 설정에 맞춰 자동으로 추가합니다."""
#     print("host :", host)


# TODO: figma mcp 관련 설치를 자동으로 !!!


# TODO: bun 설치 지원
# TODO: node 설치 지원


# @app.command()
# def remove(
#     host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
#     is_verbose: bool = Option(False, "--verbose", "-v"),
# ):
#     # code --add-mcp '{"name":"playwright","command":"npx","args":["@playwright/mcp@latest"]}'
#     # code-insiders --add-mcp '{"name":"playwright","command":"npx","args":["@playwright/mcp@latest"]}'
#     print("host :", host)


# @app.command()
# def check(
#     host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
#     is_verbose: bool = Option(False, "--verbose", "-v"),
# ):
#     """설정 파일의 설정 오류 검사"""
#     pass


# config 에서는 list/run 명령을 지원하지 않겠습니다.
app.registered_commands = [
    cmd
    for cmd in app.registered_commands
    if cmd.name not in ("list", "run")
    and cmd.callback.__name__
    not in (
        "list",
        "run",
    )
]


if __name__ == "__main__":
    app()

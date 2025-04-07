import json

from click import ClickException
from rich.console import Console
from typer import Argument, Exit, Option, confirm, prompt

from pyhub.mcptools.core.cli import app
from pyhub.mcptools.setup import tools  # noqa
from pyhub.mcptools.setup.choices import McpHostChoices
from pyhub.mcptools.setup.utils import get_config_path, open_with_default_editor, read_config_file

console = Console()


@app.command(name="print")
def print_(
    host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """MCP 설정 출력"""

    path = get_config_path(host, is_verbose)
    with path.open("rt", encoding="utf-8") as f:
        console.print(f.read())


@app.command()
def edit(
    host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """가용 에디터로 MCP 설정 파일 편집"""
    config_path = get_config_path(host)
    open_with_default_editor(config_path, is_verbose)


# @app.command()
# def add(
#     host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
#     is_verbose: bool = Option(False, "--verbose", "-v"),
# ):
#     """지정 MCP 설정을 현재 OS 설정에 맞춰 자동으로 추가합니다."""
#     print("host :", host)


# TODO: figma mcp 관련 설치를 자동으로 !!!


@app.command()
def remove(
    host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """MCP 설정 파일에서 지정 서버 설정 제거"""

    with read_config_file(get_config_path(host, is_verbose)) as config_data:
        if not isinstance(config_data, dict):
            raise ClickException(f"[ERROR] 설정파일이 잘못된 타입 : {type(config_data).__name__}")

        mcp_servers = config_data.get("mcpServers", {})
        if len(mcp_servers) == 0:
            raise ClickException("등록된 mcpServers 설정이 없습니다.")

    console.print(f"{len(mcp_servers)}개의 MCP 서버가 등록되어있습니다.")

    # 서버 키 목록을 표시하고 선택 받기
    server_keys = list(mcp_servers.keys())

    for i, key in enumerate(server_keys, 1):
        console.print(f"[{i}] {key}")

    def validator_range(v):
        v = int(v)
        if 0 <= v - 1 < len(server_keys):
            return v
        raise ValueError

    # choice >= 1
    choice: int = prompt(
        "제거할 MCP 서버 번호를 선택하세요",
        type=validator_range,
        prompt_suffix=": ",
        show_choices=False,
    )

    idx = choice - 1
    selected_key = server_keys[idx]

    # 확인 메시지
    if not confirm(f"설정에서 '{selected_key}' 서버를 제거하시겠습니까?"):
        console.print("[yellow]작업이 취소되었습니다.[/yellow]")
        raise Exit(0)

    # 서버 제거
    del mcp_servers[selected_key]
    config_data["mcpServers"] = mcp_servers

    # 설정 파일에 저장
    config_path = get_config_path(host, is_verbose)
    with open(config_path, "wt", encoding="utf-8") as f:
        json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
        f.write(json_str)

    console.print(f"[green]'{selected_key}' 서버가 성공적으로 제거했습니다.[/green]")


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
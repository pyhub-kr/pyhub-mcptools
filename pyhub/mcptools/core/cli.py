import json
import re
import shutil
import sys
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Optional, Sequence

import typer
from asgiref.sync import async_to_sync
from click import ClickException
from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table

from pyhub.mcptools.core.choices import McpHostChoices, TransportChoices
from pyhub.mcptools.core.init import mcp
from pyhub.mcptools.core.utils import get_config_path, open_with_default_editor, read_config_file
from pyhub.mcptools.core.versions import PackageVersionChecker

app = typer.Typer(add_completion=False)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    is_version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
):
    if is_version:
        try:
            v = version("pyhub-mcptools")
        except PackageNotFoundError:
            v = "not found"
        console.print(v, highlight=False)

    elif ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def run(
    transport: TransportChoices = typer.Argument(default=TransportChoices.STDIO),
    host: str = typer.Option("0.0.0.0", help="SSE Host (SSE transport 방식에서만 사용)"),
    port: int = typer.Option(8000, help="SSE Port (SSE transport 방식에서만 사용)"),
):
    """지정 transport로 MCP 서버 실행"""

    if ":" in host:
        try:
            host, port = host.split(":")
            port = int(port)
        except ValueError as e:
            raise ValueError("Host 포맷이 잘못되었습니다. --host 'ip:port' 형식이어야 합니다.") from e

    mcp.settings.host = host
    mcp.settings.port = port

    mcp.run(transport=transport)


@app.command(name="list")
def list_():
    """tools/resources/resource_templates/prompts 목록 출력"""

    tools_list()
    resources_list()
    resource_templates_list()
    prompts_list()


@app.command()
def tools_list():
    """도구 목록 출력"""
    tools = async_to_sync(mcp.list_tools)()
    print_as_table("tools", tools)


@app.command()
def tools_call(
    tool_name: str = typer.Argument(..., help="tool name"),
    tool_args: Optional[list[str]] = typer.Argument(
        None,
        help="Arguments for the tool in key=value format(e.g, x=10 y='hello world'",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """테스트 목적으로 MCP 인터페이스를 거치지 않고 지정 도구를 직접 호출 (지원 도구 목록 : tools-list 명령)"""

    arguments = {}
    if tool_args:
        for arg in tool_args:
            try:
                key, value = arg.split("=", 1)
            except ValueError as e:
                console.print(f"[red]Invalid argument format: '{arg}'. Use key=value[/red]")
                raise typer.Exit(1) from e

            # Attempt to parse value as JSON
            try:
                arguments[key] = json.loads(value)
            except json.JSONDecodeError:
                # Fallback to string if not valid JSON
                arguments[key] = value

    if is_verbose:
        console.print(f"Calling tool '{tool_name}' with arguments: {arguments}")

    return_value: Sequence[TextContent | ImageContent | EmbeddedResource]
    try:
        return_value = async_to_sync(mcp.call_tool)(tool_name, arguments=arguments)
    except ValidationError as e:
        if is_verbose:
            console.print_exception()
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        if is_verbose:
            console.print_exception()
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    else:
        if is_verbose:
            console.print(return_value)

        for ele in return_value:
            if isinstance(ele, TextContent):
                console.print(ele.text)
            elif isinstance(ele, ImageContent):
                console.print(ele)
            elif isinstance(ele, EmbeddedResource):
                console.print(ele)
            else:
                raise ValueError(f"Unexpected type : {type(ele)}")


@app.command()
def resources_list():
    """리소스 목록 출력"""
    resources = async_to_sync(mcp.list_resources)()
    print_as_table("resources", resources)


@app.command()
def resource_templates_list():
    """리소스 템플릿 목록 출력"""
    resource_templates = async_to_sync(mcp.list_resource_templates)()
    print_as_table("resource_templates", resource_templates)


@app.command()
def prompts_list():
    """프롬프트 목록 출력"""
    prompts = async_to_sync(mcp.list_prompts)()
    print_as_table("prompts", prompts)


class FormatEnum(str, Enum):
    JSON = "json"
    TABLE = "table"


@app.command()
def setup_add(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 설정에 자동 추가 (팩키징된 실행파일만 지원)"""

    current_cmd = sys.argv[0]
    current_exe_path = Path(current_cmd).resolve()

    # 뒤에 또 다른 mcptools가 나오면 매칭하지 않음 (lookahead)
    matched = re.search(r"mcptools[/.]([a-zA-Z0-9_]+)(?!.*mcptools)", str(current_exe_path))
    command_category = matched.group(1)  # ex) "excel"
    config_name = f"pyhub.mcptools.{command_category}"

    # 소스파일 실행
    if "__main__" in current_exe_path.name:
        console.print("[red]팩키징된 실행파일에 대해서만 지원합니다.[/red]")
        new_config = None

    # 윈도우 실행파일 실행
    elif current_exe_path.suffix == ".exe":
        # current_cmd 경로를 그대로 활용하면 됨
        new_config = {"command": str(current_exe_path), "args": ["run", "stdio"]}

    # 맥 실행파일 실행
    #  - macOS에서는 Claude 내에서 엑셀 프로그램에 대한 접근 권한 문제로 stdio 방식을 지원하지 않겠습니다.
    else:
        console.print("[red]macOS는 지원예정입니다.[/red]")
        raise typer.Exit(1)

        # TODO: 현재 머신에서 (현재 가상환경 포함) 가용한 mcp-proxy 명령의 절대경로를 찾습니다.
        # mcp_proxy_abs_path = "mcp-proxy"
        #
        # TODO: pyhub.mcptools.excel SSE 서버 URL 찾기
        # pyhub_mcptools_excel_sse_path = "http://localhost:9999/sse"
        #
        # new_config = {"command": mcp_proxy_abs_path, "args": [pyhub_mcptools_excel_sse_path]}

    if new_config:
        config_path = get_config_path(mcp_host, is_verbose)

        try:
            config_data = read_config_file(config_path)
        except FileNotFoundError:
            config_data = {}

        config_data.setdefault("mcpServers", {})

        if config_name in config_data["mcpServers"]:
            is_confirm = typer.confirm(f"{config_name} 설정이 이미 있습니다. 덮어쓰시겠습니까?")
            if not is_confirm:
                raise typer.Abort()

        config_data["mcpServers"][config_name] = new_config

        config_path = get_config_path(mcp_host, is_verbose)
        with open(config_path, "wt", encoding="utf-8") as f:
            json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
            f.write(json_str)

        console.print(f"'{config_path}' 경로에 {config_name} 설정을 추가했습니다.", highlight=False)
    else:
        raise typer.Exit(1)


@app.command()
def setup_print(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    fmt: FormatEnum = typer.Option(FormatEnum.JSON, "--format", "-f", help="출력 포맷"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 표준 출력"""

    config_path = get_config_path(mcp_host, is_verbose)

    try:
        config_data = read_config_file(config_path)
    except FileNotFoundError as e:
        console.print(f"{config_path} 파일이 없습니다.")
        raise typer.Abort() from e

    if fmt == FormatEnum.TABLE:
        mcp_servers = config_data.get("mcpServers", {})

        config_keys: set = set()
        for config in mcp_servers.values():
            config_keys.update(config.keys())

        config_keys: list = sorted(config_keys - {"command", "args"})

        table = Table(title=f"[bold]{len(mcp_servers)}개의 MCP 서버가 등록되어있습니다.[/bold]", title_justify="left")
        table.add_column("id")
        table.add_column("name")
        table.add_column("command")
        table.add_column("args")
        for key in config_keys:
            table.add_column(key)

        for row_idx, (name, config) in enumerate(mcp_servers.items(), start=1):
            server_config = " ".join(config.get("args", []))
            row = [str(row_idx), name, config["command"], server_config]
            for key in config_keys:
                v = config.get(key, "")
                if v:
                    row.append(repr(v))
                else:
                    row.append("")
            table.add_row(*row)

        console.print()
        console.print(table)
    else:
        console.print(json.dumps(config_data, indent=4, ensure_ascii=False))


@app.command()
def setup_edit(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 가용 에디터로 편집"""

    config_path = get_config_path(mcp_host)
    open_with_default_editor(config_path, is_verbose)


# TODO: figma mcp 관련 설치를 자동으로 !!!


@app.command()
def setup_remove(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 지정 서버 제거"""

    config_path = get_config_path(mcp_host, is_verbose)

    try:
        config_data = read_config_file(config_path)
    except FileNotFoundError as e:
        console.print(f"{config_path} 파일이 없습니다.")
        raise typer.Abort() from e

    if not isinstance(config_data, dict):
        raise ClickException(f"[ERROR] 설정파일이 잘못된 타입 : {type(config_data).__name__}")

    mcp_servers = config_data.get("mcpServers", {})
    if len(mcp_servers) == 0:
        raise ClickException("등록된 mcpServers 설정이 없습니다.")

    setup_print(mcp_host=mcp_host, fmt=FormatEnum.TABLE, is_verbose=is_verbose)

    def validator_range(v):
        v = int(v)
        if 0 <= v - 1 < len(mcp_servers):
            return v
        raise ValueError

    # choice >= 1
    choice: int = typer.prompt(
        "제거할 MCP 서버 번호를 선택하세요",
        type=validator_range,
        prompt_suffix=": ",
        show_choices=False,
    )

    idx = choice - 1
    selected_key = tuple(mcp_servers.keys())[idx]

    # 확인 메시지
    if not typer.confirm(f"설정에서 '{selected_key}' 서버를 제거하시겠습니까?"):
        console.print("[yellow]작업이 취소되었습니다.[/yellow]")
        raise typer.Exit(0)

    # 서버 제거
    del mcp_servers[selected_key]
    config_data["mcpServers"] = mcp_servers

    # 설정 파일에 저장
    config_path = get_config_path(mcp_host, is_verbose)
    with open(config_path, "wt", encoding="utf-8") as f:
        json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
        f.write(json_str)

    console.print(f"[green]'{selected_key}' 서버가 성공적으로 제거했습니다.[/green]")


@app.command()
def setup_backup(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    dest: Path = typer.Option(..., "--dest", "-d", help="복사 경로"),
    is_force: bool = typer.Option(False, "--force", "-f", help="강제 복사 여부"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 지정 경로로 백업"""

    dest_path = dest.resolve()
    src_path = get_config_path(mcp_host, is_verbose)

    if dest_path.is_dir():
        dest_path = dest_path / src_path.name

    if dest_path.exists() and not is_force:
        console.print("지정 경로에 파일이 있어 파일을 복사할 수 없습니다.")
        raise typer.Exit(1)

    try:
        shutil.copy2(src_path, dest_path)
        console.print(f"[green]설정 파일을 {dest_path} 경로로 복사했습니다.[/green]")
    except IOError as e:
        console.print(f"[red]파일 복사 중 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def setup_restore(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    src: Path = typer.Option(..., "--src", "-s", help="원본 경로"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 복원"""

    src_path = src.resolve()
    dest_path = get_config_path(mcp_host, is_verbose)

    if src_path.is_dir():
        src_path = src_path / dest_path.name

    try:
        shutil.copy2(src_path, dest_path)
        console.print("[green]설정 파일을 복원했습니다.[/green]")
    except IOError as e:
        console.print(f"[red]파일 복사 중 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def check_update():
    """최신 버전을 확인합니다."""

    # current_cmd = sys.argv[0]
    #
    # if "__main__" in current_cmd:
    #     console.print("[red]팩키징된 실행파일에 대해서만 지원합니다.[/red]")
    #     raise typer.Exit(1)

    package_name = "pyhub-mcptools"
    version_check = PackageVersionChecker.check_update(package_name, is_force=True)

    if not version_check.has_update:
        console.print(f"이미 최신 버전({version_check.installed})입니다.", highlight=False)
    else:
        latest_url = f"https://github.com/pyhub-kr/pyhub-mcptools/releases/tag/v{version_check.latest}"
        console.print(f"{latest_url} 페이지에서 최신 버전을 다운받으실 수 있습니다.")


def print_as_table(title: str, rows: list[BaseModel]) -> None:
    if len(rows) > 0:
        table = Table(title=f"[bold]{title}[/bold]", title_justify="left")

        row = rows[0]
        row_dict = row.model_dump()
        column_names = row_dict.keys()
        for name in column_names:
            table.add_column(name)

        for row in rows:
            columns = []
            for name in column_names:
                value = getattr(row, name, None)
                if value is None:
                    columns.append(f"{value}")
                else:
                    columns.append(f"[blue bold]{value}[/blue bold]")
            table.add_row(*columns)

        console.print(table)

    else:
        console.print(f"[gray]no {title}[/gray]")

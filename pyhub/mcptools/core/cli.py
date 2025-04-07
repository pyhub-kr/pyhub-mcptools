import json
import shutil
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

    if host is not None:
        if ":" in host:
            try:
                host_part, port_str = host.split(":")
                port_from_host = int(port_str)
                mcp.settings.host = host_part
                mcp.settings.port = port_from_host
            except ValueError as e:
                raise typer.BadParameter("Host 포맷이 잘못되었습니다. --host 'ip:port' 형식이어야 합니다.") from e
        else:
            mcp.settings.host = host

            # 별도 port 인자가 지정된 경우에만 설정
            if port is not None:
                mcp.settings.port = port

    elif port is not None:
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
def setup_print(
    host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    fmt: FormatEnum = typer.Option(FormatEnum.JSON, "--format", "-f", help="출력 포맷"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 표준 출력"""

    with read_config_file(get_config_path(host, is_verbose)) as config_data:
        if fmt == FormatEnum.TABLE:
            mcp_servers = config_data.get("mcpServers", [])

            config_keys = set()
            for config in mcp_servers.values():
                config_keys.update(config.keys())

            config_keys: list = sorted(config_keys - {"command", "args"})

            table = Table(
                title=f"[bold]{len(mcp_servers)}개의 MCP 서버가 등록되어있습니다.[/bold]", title_justify="left"
            )
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
    host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 가용 에디터로 편집"""

    config_path = get_config_path(host)
    open_with_default_editor(config_path, is_verbose)


# @app.command()
# def setup_add(
#     host: McpHostChoices = Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
#     is_verbose: bool = Option(False, "--verbose", "-v"),
# ):
#     """지정 MCP 설정을 현재 OS 설정에 맞춰 자동으로 추가합니다."""
#     print("host :", host)


# TODO: figma mcp 관련 설치를 자동으로 !!!


@app.command()
def setup_remove(
    host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 지정 서버 제거"""

    with read_config_file(get_config_path(host, is_verbose)) as config_data:
        if not isinstance(config_data, dict):
            raise ClickException(f"[ERROR] 설정파일이 잘못된 타입 : {type(config_data).__name__}")

        mcp_servers = config_data.get("mcpServers", {})
        if len(mcp_servers) == 0:
            raise ClickException("등록된 mcpServers 설정이 없습니다.")

    setup_print(host=host, fmt=FormatEnum.TABLE, is_verbose=is_verbose)

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
    config_path = get_config_path(host, is_verbose)
    with open(config_path, "wt", encoding="utf-8") as f:
        json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
        f.write(json_str)

    console.print(f"[green]'{selected_key}' 서버가 성공적으로 제거했습니다.[/green]")


@app.command()
def setup_backup(
    host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    dest: Path = typer.Option(..., "--dest", "-d", help="복사 경로"),
    is_force: bool = typer.Option(False, "--force", "-f", help="강제 복사 여부"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 지정 경로로 백업"""

    dest_path = dest.resolve()
    src_path = get_config_path(host, is_verbose)

    if dest_path.is_dir():
        dest_path = dest_path / src_path.name

    if dest_path.exists() and not is_force:
        console.print("지정 경로에 파일이 있어 파일을 복사할 수 없습니다.")
        raise typer.Exit(1)

    try:
        shutil.copy2(src_path, dest_path)
        console.print("[green]설정 파일을 성공적으로 복사했습니다.[/green]")
    except IOError as e:
        console.print(f"[red]파일 복사 중 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def setup_restore(
    host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    src: Path = typer.Option(..., "--src", "-s", help="원본 경로"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 복원"""

    src_path = src.resolve()
    dest_path = get_config_path(host, is_verbose)

    if src_path.is_dir():
        src_path = src_path / dest_path.name

    try:
        shutil.copy2(src_path, dest_path)
        console.print("[green]설정 파일을 복원했습니다.[/green]")
    except IOError as e:
        console.print(f"[red]파일 복사 중 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


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
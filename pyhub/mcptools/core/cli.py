import json
from importlib.metadata import version, PackageNotFoundError
from typing import Optional, Sequence

import typer
from asgiref.sync import async_to_sync
from mcp.types import TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table
from typer import Argument, Option

from pyhub.mcptools.core.choices import TransportChoices
from pyhub.mcptools.core.init import mcp

app = typer.Typer()
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
            except ValueError:
                raise typer.BadParameter("Host 포맷이 잘못되었습니다. --host 'ip:port' 형식이어야 합니다.")
        else:
            mcp.settings.host = host

            # 별도 port 인자가 지정된 경우에만 설정
            if port is not None:
                mcp.settings.port = port

    elif port is not None:
        mcp.settings.port = port

    mcp.run(transport=transport)


@app.command()
def call(
    tool_name: str = Argument(..., help="tool name"),
    tool_args: Optional[list[str]] = Argument(
        None,
        help="Arguments for the tool in key=value format(e.g, x=10 y='hello world'",
    ),
    is_verbose: bool = Option(False, "--verbose", "-v"),
):
    """테스트 목적으로 MCP 인터페이스를 거치지 않고 지정 도구를 직접 호출"""

    arguments = {}
    if tool_args:
        for arg in tool_args:
            try:
                key, value = arg.split("=", 1)
            except ValueError:
                console.print(f"[red]Invalid argument format: '{arg}'. Use key=value[/red]")
                raise typer.Exit(1)

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
        raise typer.Exit(1)
    except Exception as e:
        if is_verbose:
            console.print_exception()
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
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


@app.command(name="list")
def list_():
    """tools/resources/resource_templates/prompts 목록 출력"""

    tools = async_to_sync(mcp.list_tools)()
    resources = async_to_sync(mcp.list_resources)()
    resource_templates = async_to_sync(mcp.list_resource_templates)()
    prompts = async_to_sync(mcp.list_prompts)()

    print_as_table("tools", tools)
    print_as_table("resources", resources)
    print_as_table("resource_templates", resource_templates)
    print_as_table("prompts", prompts)


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
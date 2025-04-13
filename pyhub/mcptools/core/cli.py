import asyncio
import json
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable, Optional, Sequence

import httpx
import typer
from asgiref.sync import async_to_sync
from click import Choice, ClickException
from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from mcp.types import EmbeddedResource, ImageContent, TextContent
from mcp_proxy.sse_client import run_sse_client
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table
from typer.core import TyperCommand
from typer.models import CommandFunctionType, OptionInfo

from pyhub.mcptools.core.choices import OS, FormatChoices, McpHostChoices, TransportChoices
from pyhub.mcptools.core.init import mcp
from pyhub.mcptools.core.updater import apply_update
from pyhub.mcptools.core.utils import (
    get_config_path,
    get_log_dir_path,
    get_log_path_list,
    open_with_default_editor,
    read_config_file,
)
from pyhub.mcptools.core.utils.process import kill_mcp_host_process
from pyhub.mcptools.core.utils.sse import is_mcp_sse_server_alive
from pyhub.mcptools.core.versions import PackageVersionChecker


class PyhubTyper(typer.Typer):
    def command(
        self,
        *args,
        experimental: bool = False,
        **kwargs,
    ) -> Callable[[CommandFunctionType], TyperCommand]:
        if experimental and not settings.EXPERIMENTAL:

            def empty_decorator(f: CommandFunctionType) -> CommandFunctionType:
                return f

            return empty_decorator

        return super().command(*args, **kwargs)


app = PyhubTyper(add_completion=False)
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
    host: str = typer.Option("127.0.0.1", help="SSE Host (SSE transport 방식에서만 사용)"),
    port: int = typer.Option(8000, help="SSE Port (SSE transport 방식에서만 사용)"),
    is_experimental: bool = typer.Option(False, "--experimental"),
):
    """지정 transport로 MCP 서버 실행 (디폴트: stdio)"""

    if transport == TransportChoices.STDIO:
        mcp.run(transport="stdio")

    else:
        if is_experimental is False:
            console.print(f"Starting SSE MCP Server on {host}:{port}", highlight=False)
            mcp.settings.host = host
            mcp.settings.port = port
            mcp.run(transport="sse")

        else:
            console.print(f"Starting Experimental SSE MCP Server on {host}:{port}", highlight=False)

            import uvicorn

            from pyhub.mcptools.core.asgi import application as asgi_application

            if ":" in host:
                try:
                    host, port = host.split(":")
                    port = int(port)
                except ValueError as e:
                    raise ValueError("Host 포맷이 잘못되었습니다. --host 'ip:port' 형식이어야 합니다.") from e

            uvicorn.run(
                app=asgi_application,
                host=host,
                port=port,
                reload=False,
                workers=1,
            )


@app.command()
def run_sse_proxy(
    sse_url: str = typer.Argument("http://127.0.0.1:8000/sse", help="SSE Endpoint"),
):
    """지정한 SSE Endpoint와 stdio를 통해 프록시 연결을 수행 (default: http://127.0.0.1:8000/sse)

    서버로부터 수신된 SSE 이벤트는 표준 출력(stdout)으로 전달되며, 표준 입력(stdin)으로부터 입력을 수신하여
    필요한 경우 서버로 전송하거나 처리할 수 있습니다. 이 명령은 LLM 응답의 스트리밍 중계를 위한
    표준 입출력 기반 인터페이스를 제공합니다.

    기본 SSE Endpoint는 'http://127.0.0.1:8000/sse'이며, --sse-url 옵션으로 변경 가능합니다.
    """

    # https://github.com/sparfenyuk/mcp-proxy?tab=readme-ov-file#1-stdio-to-sse

    headers = {}

    # 인증이 필요할 때, 헤더 활용
    # headers["Authorization"] = f"Bearer {api_access_token}"

    try:
        asyncio.run(run_sse_client(sse_url, headers=headers))
    except Exception as e:
        if sys.version_info >= (3, 11) and isinstance(e, ExceptionGroup):
            for sub in e.exceptions:
                if isinstance(sub, httpx.ConnectError):
                    console.print(f"[red]SSE 연결 실패: {sub}[/red]")
                    raise typer.Exit(1) from e
        console.print(f"[red]예외 발생: {e}[/red]")
        raise typer.Exit(1) from e


@app.command(name="list")
def list_():
    """tools/resources/resource_templates/prompts 목록 출력"""

    tools_list()
    resources_list()
    resource_templates_list()
    prompts_list()


@app.command()
def tools_list(
    verbosity: int = typer.Option(
        2,
        "--verbosity",
        "-v",
        help="출력 상세 수준",
        min=1,
        max=3,
    ),
):
    """도구 목록 출력"""

    # list_ 함수에서 tools_list 함수 직접 호출 시에 디폴트 인자가 적용되면, OptionInfo 객체가 적용됩니다.
    if isinstance(verbosity, OptionInfo):
        verbosity = verbosity.default

    tools = async_to_sync(mcp.list_tools)()

    # verbosity 수준에 따라 표시할 컬럼 결정
    columns = ["name"]
    if verbosity >= 2:
        columns.append("description")
    if verbosity >= 3:
        columns.append("inputSchema")

    print_as_table("tools", tools, columns=columns)


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
            # console.print는 출력하는 과정에서 raw string을 출력하지 않고,
            # 대괄호 등을 포맷팅 제어 문자로서 사용하기에 print 로서 raw string 출력
            if isinstance(ele, TextContent):
                print(ele.text)
            elif isinstance(ele, ImageContent):
                print(ele)
            elif isinstance(ele, EmbeddedResource):
                print(ele)
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


@app.command()
def setup_add(
    mcp_host: McpHostChoices = typer.Argument(McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    transport: TransportChoices = typer.Option(TransportChoices.STDIO, "--transport", "-t"),
    sse_url: Optional[str] = typer.Option(None, "--sse-url", "-s", help="SSE Endpoint (SSE transport 방식에서만 사용)"),
    config_name: Optional[str] = typer.Option("pyhub.mcptools", "--config-name", "-n", help="Server Name"),
    environment: Optional[list[str]] = typer.Option(
        None,
        "--environment",
        "-e",
        help="환경변수 설정 (예: -e KEY=VALUE). 여러 번 사용 가능",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
    is_dry: bool = typer.Option(False, "--dry", help="실제 적용하지 않고 설정값만 확인합니다."),
):
    """[MCP 설정파일] 설정에 자동 추가 (팩키징된 실행파일만 지원)"""

    if transport == TransportChoices.SSE and sse_url is None:
        sse_url = "http://127.0.0.1:8000/sse"

    if sse_url:
        if sse_url.startswith(("http://", "https://")) is False:
            console.print(f"[red]ERROR: --sse-url 인자가 URL 포맷이 아닙니다.[/red]")
            raise typer.Exit(1)

        if transport == TransportChoices.STDIO:
            console.print(f"[yellow]INFO: --sse-url 인자가 지정되어 연결 방식을 SSE 방식으로 조정합니다.[/yellow]")
            transport = TransportChoices.SSE

    # 환경변수 처리
    env_dict = {}
    if environment:
        for env_str in environment:
            try:
                key, value = env_str.split("=", 1)
                env_dict[key.strip()] = value.strip()
            except ValueError as e:
                console.print(f"[red]잘못된 환경변수 형식: {env_str}[/red]")
                raise typer.Exit(1) from e

    current_cmd = sys.argv[0]
    current_exe_path = str(Path(current_cmd).resolve())

    if getattr(sys, "frozen", False) is False:
        # 소스 파일을 직접 실행할 때, 현재 실행된 python 경로를 파이썬 entry 소스 파일 경로 앞에 추가
        current_exe_path = sys.executable + " " + current_exe_path

    if transport == TransportChoices.STDIO:
        run_command = f"{current_exe_path} run stdio"

    else:
        if async_to_sync(is_mcp_sse_server_alive)(sse_url=sse_url):
            if is_verbose:
                console.print(f"[green]✔ SSE 서버 연결 성공: {sse_url}[/green]")
        else:
            raise typer.BadParameter(
                f"""{sse_url} 주소의 서버에 접속할 수 없습니다. 먼저 서버를 실행시켜주세요.

ex) {current_exe_path} run sse
"""
            )

        run_command = f"{current_exe_path} run-sse-proxy {sse_url}"

    words = run_command.split()
    new_config = {
        "command": words[0],
        "args": words[1:],
    }
    if env_dict:
        new_config["env"] = env_dict

    if is_dry is True:
        console.print(json.dumps(new_config, indent=4, ensure_ascii=False))

    else:
        config_path = get_config_path(mcp_host, is_verbose, allow_exit=True)

        try:
            config_data = read_config_file(config_path)
        except FileNotFoundError:
            config_data = {}

        config_data.setdefault("mcpServers", {})

        if config_name in config_data["mcpServers"]:
            is_confirm = typer.confirm(f"{config_path} 설정에 {config_name} 설정이 이미 있습니다. 덮어쓰시겠습니까?")
            if not is_confirm:
                raise typer.Abort()

        config_data["mcpServers"][config_name] = new_config

        # Claude 설정 폴더가 없다면, FileNotFoundError 예외가 발생합니다.
        try:
            with open(config_path, "wt", encoding="utf-8") as f:
                json_str = json.dumps(config_data, indent=2, ensure_ascii=False)
                f.write(json_str)
        except FileNotFoundError as e:
            console.print("[red]Claude Desktop 프로그램을 먼저 설치해주세요. - https://claude.ai/download[/red]")
            raise typer.Abort() from e

        console.print(f"'{config_path}' 경로에 {config_name} 설정을 추가했습니다.", highlight=False)


@app.command()
def setup_print(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    fmt: FormatChoices = typer.Option(FormatChoices.JSON, "--format", "-f", help="출력 포맷"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 표준 출력"""

    config_path = get_config_path(mcp_host, is_verbose, allow_exit=True)

    try:
        config_data = read_config_file(config_path)
    except FileNotFoundError as e:
        console.print(f"{config_path} 파일이 없습니다.")
        raise typer.Abort() from e

    if fmt == FormatChoices.TABLE:
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

    config_path = get_config_path(mcp_host, is_verbose, allow_exit=True)
    open_with_default_editor(config_path, is_verbose)


# TODO: figma mcp 관련 설치를 자동으로 !!!


@app.command()
def setup_remove(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """[MCP 설정파일] 지정 서버 제거"""

    config_path = get_config_path(mcp_host, is_verbose, allow_exit=True)

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

    setup_print(mcp_host=mcp_host, fmt=FormatChoices.TABLE, is_verbose=is_verbose)

    # choice >= 1
    choice: str = typer.prompt(
        "제거할 MCP 서버 번호를 선택하세요",
        type=Choice(list(map(str, range(1, len(mcp_servers) + 1)))),
        prompt_suffix=": ",
        show_choices=False,
    )

    idx = int(choice) - 1
    selected_key = tuple(mcp_servers.keys())[idx]

    # 확인 메시지
    if not typer.confirm(f"설정에서 '{selected_key}' 서버를 제거하시겠습니까?"):
        console.print("[yellow]작업이 취소되었습니다.[/yellow]")
        raise typer.Exit(0)

    # 서버 제거
    del mcp_servers[selected_key]
    config_data["mcpServers"] = mcp_servers

    # 설정 파일에 저장
    config_path = get_config_path(mcp_host, is_verbose, allow_exit=True)
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
    src_path = get_config_path(mcp_host, is_verbose, allow_exit=True)

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
    dest_path = get_config_path(mcp_host, is_verbose, allow_exit=True)

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

    if getattr(sys, "frozen", False) is False:
        console.print("[red]패키징된 실행파일에서만 버전 확인을 지원합니다.[/red]")
        raise typer.Exit(1)

    package_name = "pyhub-mcptools"
    version_check = PackageVersionChecker.check_update(package_name, is_force=True)

    if not version_check.has_update:
        console.print(f"이미 최신 버전({version_check.installed})입니다.", highlight=False)
    else:
        latest_url = f"https://github.com/pyhub-kr/pyhub-mcptools/releases/tag/v{version_check.latest}"
        console.print(f"{latest_url} 페이지에서 최신 버전을 다운받으실 수 있습니다.")


@app.command()
def update(
    target_version: Optional[str] = typer.Argument(
        None, help="업데이트할 버전. 생략하면 최신 버전으로 업데이트합니다. (ex: 0.5.0)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="이미 최신 버전이라도 강제로 업데이트합니다."),
    yes: bool = typer.Option(False, "--yes", "-y", help="업데이트 전 확인하지 않고 바로 진행합니다."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """최신 버전으로 업데이트합니다."""

    if getattr(sys, "frozen", False) is False:
        console.print("[red]패키징된 실행파일에서만 자동 업데이트를 지원합니다.[/red]")
        raise typer.Exit(1)

    # 버전 포맷 검사 (숫자.숫자.숫자)
    if target_version and not re.match(r"^\d+\.\d+\.\d+$", target_version):
        console.print(f"[red]버전 형식이 잘못되었습니다. '숫자.숫자.숫자' 형식이어야 합니다: {target_version}[/red]")
        raise typer.Exit(1)

    package_name = "pyhub-mcptools"
    version_check = PackageVersionChecker.check_update(package_name)

    if target_version:
        version_check.latest = target_version
        console.print(f"[blue]지정된 버전({target_version})으로 업데이트합니다.[/blue]")

    elif not version_check.has_update and not force:
        console.print(f"이미 최신 버전({version_check.installed})입니다.", highlight=False)
        raise typer.Exit(0)

    elif not version_check.has_update and force:
        version_check.latest = version_check.installed
        console.print(f"[yellow]같은 버전({version_check.installed})이라도 강제 업데이트를 진행합니다.[/yellow]")

    for mcp_host in McpHostChoices:
        if mcp_host in (McpHostChoices.CLAUDE,):
            if typer.confirm(f"{mcp_host}를(을) 강제 종료하시겠습니까?"):
                kill_mcp_host_process(mcp_host)
                console.print(f"[green]Killed {mcp_host} processes[/green]")

    # 업데이트 진행 여부를 한 번 더 확인합니다.
    if not yes:
        confirm = typer.confirm(
            f"현재 버전 {version_check.installed}에서 {version_check.latest}로 업데이트하시겠습니까?"
        )
        if not confirm:
            console.print("업데이트를 취소하셨습니다.")
            raise typer.Exit(0)

    console.print(f"[green]업데이트할 버전 {version_check.latest}[/green]")

    apply_update(version_check.latest, verbose)


@app.command()
def kill(
    mcp_host: McpHostChoices = typer.Argument(..., help="프로세스를 죽일 MCP 클라이언트"),
):
    """MCP 설정 적용을 위해 Claude 등의 MCP 클라이언트 프로세스를 죽입니다."""

    kill_mcp_host_process(mcp_host)

    console.print(f"[green]Killed {mcp_host.value} processes[/green]")


@app.command()
def release_note():
    """릴리스 노트 출력"""

    url = "https://raw.githubusercontent.com/pyhub-kr/pyhub-mcptools/refs/heads/main/docs/release-notes.md"

    try:
        response = httpx.get(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        print(response.text)
    except httpx.HTTPError as e:
        console.print(f"[red]릴리스 노트를 가져오는 중 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]예상치 못한 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def log_folder(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    is_open: bool = typer.Option(False, "--open", "-o", help="OS의 기본 파일 탐색기로 로그 폴더 열기"),
):
    """MCP 호스트 프로그램의 로그 폴더 경로를 출력하거나 파일 탐색기로 엽니다.

    Args:
        mcp_host: MCP 호스트 프로그램 선택 (기본값: CLAUDE)
        is_open: True일 경우 OS의 기본 파일 탐색기로 로그 폴더를 엽니다.
    """
    dir_path = get_log_dir_path(mcp_host)

    if is_open:
        match OS.get_current():
            case OS.WINDOWS:
                subprocess.run(["explorer", dir_path])
            case OS.MACOS:
                subprocess.run(["open", dir_path])
            case _:
                try:
                    subprocess.run(["xdg-open", dir_path])
                except FileNotFoundError:
                    console.print("[yellow]현재 OS에서는 디렉토리 열기를 지원하지 않습니다.[/yellow]")
                    console.print(f"로그 디렉토리 경로: {dir_path}")
    else:
        # 경로만 출력
        console.print(f"로그 디렉토리 경로: {dir_path}")


@app.command()
def log_tail(
    mcp_host: McpHostChoices = typer.Argument(default=McpHostChoices.CLAUDE, help="MCP 호스트 프로그램"),
    name: Optional[str] = typer.Option(None, "--name"),
    n_lines: int = typer.Option(10, "--lines", "-n", help="마지막 N줄만 출력"),
    is_follow: bool = typer.Option(False, "--follow", "-f", help="로그 파일을 모니터링하면서 계속 출력"),
    is_verbose: bool = typer.Option(False, "--verbose", "-v"),
    timestamp_format: str = typer.Option(
        "%Y-%m-%d %H:%M:%S",
        "--timestamp-format",
        "-t",
        help="타임스탬프 출력 포맷",
    ),
):
    """MCP 호스트 프로그램의 로그 파일을 tail 형식으로 출력합니다.

    여러 로그 파일이 있는 경우 선택할 수 있으며, 로그의 타임스탬프는 로컬 시간대로 변환되어 출력됩니다.

    Args:
        mcp_host: MCP 호스트 프로그램 선택 (기본값: CLAUDE)
        name: 로그 파일명에 포함된 문자열로 필터링
        n_lines: 출력할 마지막 라인 수 (기본값: 10)
        is_follow: 실시간으로 로그 파일 모니터링 (tail -f와 유사)
        is_verbose: 상세 정보 출력 여부
        timestamp_format: 타임스탬프 출력 포맷 (기본값: "%Y-%m-%d %H:%M:%S")
    """
    try:
        path_list = get_log_path_list(mcp_host)
        if not path_list:
            console.print(f"[yellow]{mcp_host} 로그 파일이 없습니다.[/yellow]")
            raise typer.Exit(0)

        # name 인자가 지정된 경우 필터링
        if name:
            path_list = [p for p in path_list if name in p.name]
            if not path_list:
                console.print(
                    f"[yellow]{mcp_host} 로그 파일 중에 파일명에 '{name}' 문자열이 "
                    f"포함된 로그 파일이 없습니다.[/yellow]"
                )
                raise typer.Exit(0)

        # 파일들을 찾아서 수정시각 기준으로 내림차순 정렬
        path_list = sorted(path_list, key=lambda p: p.stat().st_mtime, reverse=True)

        # 단일 경로인 경우 자동 선택
        if len(path_list) == 1:
            path = path_list[0]
            if is_verbose:
                console.print(f"\n단일 로그 파일을 자동 선택합니다: {path}")
        else:
            table = Table()
            table.add_column("id", justify="right")
            table.add_column("name")
            table.add_column("mtime")
            table.add_column("size", justify="right")  # 우측 정렬 지정

            def get_size_color(size_bytes: int) -> str:
                if size_bytes >= 100 * 1024 * 1024:  # 100MB 이상
                    return "red bold"
                elif size_bytes >= 10 * 1024 * 1024:  # 10MB 이상
                    return "yellow bold"
                elif size_bytes >= 1024 * 1024:  # 1MB 이상
                    return "green bold"
                elif size_bytes >= 100 * 1024:  # 100KB 이상
                    return "blue"
                else:
                    return "white"

            def replace_timestamp(match):
                utc_str = match.group(1)
                # UTC 시간을 파싱
                utc_dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                local_dt = utc_dt.astimezone(tz)
                # 시간과 함께 timezone 정보도 출력
                return f"{local_dt.strftime(timestamp_format)}"

            for idx, path in enumerate(path_list, start=1):
                stat = path.stat()
                mtime_timestamp = stat.st_mtime
                tz = timezone.get_current_timezone()
                mtime_datetime = datetime.fromtimestamp(mtime_timestamp, tz=tz)

                table.add_row(
                    str(idx),
                    path.name,
                    mtime_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    f"[{get_size_color(stat.st_size)}]{filesizeformat(stat.st_size)}[/{get_size_color(stat.st_size)}]",
                )

            console.print(table)

            choice: str = typer.prompt(
                "출력할 로그를 선택하세요",
                type=Choice(list(map(str, range(1, len(path_list) + 1)))),
                prompt_suffix=": ",
                show_choices=False,
            )

            idx = int(choice) - 1
            path = path_list[idx]

        if is_verbose:
            console.print(f"\n로그 파일 경로: {path}")

        with open(path, "r", encoding="utf-8") as f:
            # 파일의 마지막 N줄만 읽기
            last_lines = deque(f, n_lines)

            # ISO 8601 형식의 UTC 타임스탬프를 찾아서 현재 timezone으로 변환
            iso_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)")
            tz = timezone.get_current_timezone()

            for line in last_lines:
                converted_line = iso_pattern.sub(replace_timestamp, line)
                print(converted_line, end="")

            if is_follow:
                # 파일의 끝으로 이동
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        # 실시간 모니터링에서도 타임스탬프 변환 적용
                        converted_line = iso_pattern.sub(replace_timestamp, line)
                        print(converted_line, end="")
                    else:
                        # 새로운 라인이 없으면 잠시 대기
                        time.sleep(0.1)
    except KeyboardInterrupt:
        console.print("\n로그 모니터링을 종료합니다.")
    except FileNotFoundError as e:
        console.print(f"\n[red]로그 파일을 찾을 수 없습니다: {path}[/red]")
        raise typer.Exit(1) from e
    except PermissionError as e:
        console.print(f"\n[red]로그 파일에 접근 권한이 없습니다: {path}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]예상치 못한 오류가 발생했습니다: {e}[/red]")
        raise typer.Exit(1) from e


def print_as_table(title: str, rows: list[BaseModel], columns: Optional[list[str]] = None) -> None:
    if len(rows) > 0:
        table = Table(title=f"[bold]{title}[/bold]", title_justify="left")

        row = rows[0]
        row_dict = row.model_dump()

        column_names = columns or row_dict.keys()
        column_names = [name for name in column_names if name in row_dict]

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

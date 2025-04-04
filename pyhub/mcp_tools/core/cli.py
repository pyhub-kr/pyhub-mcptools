import typer
from asgiref.sync import async_to_sync
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from .choices import TransportChoices
from .init import mcp

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def run(
    transport: TransportChoices = typer.Option(default=TransportChoices.STDIO),
):
    """지정 transport로 MCP 서버 실행"""
    mcp.run(transport=transport)


@app.command(name="list")
def list_():
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

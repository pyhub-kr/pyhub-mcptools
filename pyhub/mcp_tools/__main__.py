import typer
from rich.console import Console

app = typer.Typer(
    pretty_exceptions_show_locals=False,
)
console = Console()


logo = """
██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ███╗   ███╗ ██████╗██████╗ 
██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ████╗ ████║██╔════╝██╔══██╗
██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██╔████╔██║██║     ██████╔╝
██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██║╚██╔╝██║██║     ██╔═══╝
██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ██║ ╚═╝ ██║╚██████╗██║
╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚═╝     ╚═╝ ╚═════╝╚═╝

  Life is short. You need Python/Django.
  I will be your pacemaker.
  https://mcp.pyhub.kr
"""


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(logo)


if __name__ == "__main__":
    app()

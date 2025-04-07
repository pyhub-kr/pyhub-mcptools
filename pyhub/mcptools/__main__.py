from importlib import import_module

import typer

from pyhub.mcptools.core.cli import app, console

logo = """
██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗
██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗
██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝
██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗
██║        ██║   ██║  ██║╚██████╔╝██████╔╝
╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝

███╗   ███╗ ██████╗██████╗    ████████╗ ██████╗  ██████╗ ██╗     ███████╗
████╗ ████║██╔════╝██╔══██╗   ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝
██╔████╔██║██║     ██████╔╝      ██║   ██║   ██║██║   ██║██║     ███████╗
██║╚██╔╝██║██║     ██╔═══╝       ██║   ██║   ██║██║   ██║██║     ╚════██║
██║ ╚═╝ ██║╚██████╗██║           ██║   ╚██████╔╝╚██████╔╝███████╗███████║
╚═╝     ╚═╝ ╚═════╝╚═╝           ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝

  Life is short. You need 파이썬사랑방.
  I will be your pacemaker.
  https://mcp.pyhub.kr
"""


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    # 사용할 Tools 들을 임포트
    import_module("pyhub.mcptools.excel.tools")

    if ctx.invoked_subcommand is None:
        console.print(logo)
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()

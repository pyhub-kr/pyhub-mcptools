from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

import typer

from django.conf import settings
from pyhub.mcptools.core.choices import OS
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
    else:
        if ctx.invoked_subcommand is None:
            console.print(logo)
            console.print(ctx.get_help())


if __name__ == "__main__":
    # 아래 freeze_support 를 수행하지 않으면,
    # PyInstaller로 패키징된 실행 파일을 실행할 때, multiprocessing 모듈이 포크(fork) 모드로 실행되려다 실패
    # PyInstaller가 만든 바이너리는 subprocess가 스스로 다시 실행될 때 sys.argv에 자동으로 --multiprocessing-fork를 붙이는데,
    # 당신의 CLI 코드가 그것을 인식하지 못하고 에러를 냅니다.

    import multiprocessing

    multiprocessing.freeze_support()

    #
    # commands
    #
    import_module("pyhub.mcptools.fs.__main__")
    import_module("pyhub.mcptools.maps.__main__")
    import_module("pyhub.mcptools.search.__main__")

    import_module("pyhub.mcptools.microsoft.__main__")

    if OS.current_is_macos():
        import_module("pyhub.mcptools.apple.__main__")

    if settings.USE_IMAGES_TOOLS:
        import_module("pyhub.mcptools.images.__main__")

    if settings.USE_PYTHON_TOOLS:
        import_module("pyhub.mcptools.python.__main__")

    if settings.USE_SENTIMENT_TOOLS:
        import_module("pyhub.mcptools.sentiment.__main__")

    #
    # Tools
    #
    import_module("pyhub.mcptools.fs.tools")
    import_module("pyhub.mcptools.maps.tools")
    # import_module("pyhub.mcptools.music.tools")
    import_module("pyhub.mcptools.search.tools")

    import_module("pyhub.mcptools.microsoft.tools")

    if OS.current_is_macos():
        import_module("pyhub.mcptools.apple.tools")

    if settings.USE_IMAGES_TOOLS:
        import_module("pyhub.mcptools.images.tools")

    if settings.USE_PYTHON_TOOLS:
        import_module("pyhub.mcptools.python.tools")

    if settings.USE_SENTIMENT_TOOLS:
        import_module("pyhub.mcptools.sentiment.tools")

    app()

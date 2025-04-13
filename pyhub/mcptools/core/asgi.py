import os

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route

from pyhub.mcptools.core.init import mcp

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pyhub.mcptools.core.settings",
)

django_asgi_app = get_asgi_application()


async def redirect_root(request):
    return RedirectResponse(url="/app/")


application = Starlette(
    routes=[
        Route("/", endpoint=redirect_root),  # 루트 경로를 명시적으로 처리
        Mount("/app", app=django_asgi_app),  # 끝의 슬래시 제거
        Mount("/", app=mcp.sse_app()),  # mcp 앱을 루트에 마운트하여 /sse, /messages 직접 처리
    ]
)

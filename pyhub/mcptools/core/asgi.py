import importlib
import logging
import os
from inspect import isclass
from typing import Dict

from asgiref.typing import ASGIApplication
from channels.consumer import AsyncConsumer, SyncConsumer
from channels.routing import ChannelNameRouter, ProtocolTypeRouter
from django.apps import apps
from django.core.asgi import get_asgi_application

from pyhub.mcptools.core.init import mcp

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pyhub.mcptools.core.settings",
)

django_asgi_app = get_asgi_application()


sse_app = mcp.sse_app()

logger = logging.getLogger(__name__)


def discover_workers() -> Dict[str, ASGIApplication]:
    workers = {}
    for app_config in apps.get_app_configs():
        try:
            mod = importlib.import_module(f"{app_config.name}.workers")
        except ModuleNotFoundError:
            continue

        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isclass(obj)
                and issubclass(obj, (AsyncConsumer, SyncConsumer))
                and obj not in (AsyncConsumer, SyncConsumer)
            ):
                channel_name = getattr(obj, "channel_name", None)
                if channel_name:
                    workers[channel_name] = obj.as_asgi()
                    logger.info(
                        f"Registered worker - Channel: {channel_name}, " f"Consumer: {obj.__module__}.{obj.__name__}"
                    )
    return workers


async def http_dispatch(scope, receive, send):
    """HTTP 요청. FastMCP SSE ASGI App과 Django ASGI App 분기"""

    if scope["type"] != "http":
        return

    _path = scope.get("path", "")
    if _path in (mcp.settings.sse_path, mcp.settings.message_path):
        await sse_app(scope, receive, send)
    else:
        await django_asgi_app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": http_dispatch,
        # "websocket": ...,
        "channel": ChannelNameRouter(discover_workers()),
    }
)

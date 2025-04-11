import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MusicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.mcptools.music"

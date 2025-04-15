import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ImagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.mcptools.images"

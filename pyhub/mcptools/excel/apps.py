import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ExcelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.mcptools.excel"

from django.db.models import TextChoices


class TransportChoices(TextChoices):
    STDIO = "stdio"
    SSE = "sse"


class McpHostChoices(TextChoices):
    CLAUDE = "claude"
    # CURSOR = "cursor"

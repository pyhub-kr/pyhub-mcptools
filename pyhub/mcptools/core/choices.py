from django.db.models import TextChoices


class TransportChoices(TextChoices):
    STDIO = "stdio"
    SSE = "sse"

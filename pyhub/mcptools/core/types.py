from enum import Enum


class FormatEnum(str, Enum):
    JSON = "json"
    TABLE = "table"


class McpClientEnum(str, Enum):
    # https://modelcontextprotocol.io/clients
    CLAUDE = "claude"
    CURSOR = "cursor"

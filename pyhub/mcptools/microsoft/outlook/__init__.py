from pyhub.mcptools.core.choices import OS

if OS.current_is_windows():
    from pyhub.mcptools.microsoft.outlook.win import (
        get_email,
        get_emails,
        get_folders,
        outlook_connection,
        send_email,
    )
elif OS.current_is_macos():
    from pyhub.mcptools.microsoft.outlook.macos import (
        get_email,
        get_emails,
        get_folders,
        outlook_connection,
        send_email,
    )

__all__ = ["outlook_connection", "get_email", "get_emails", "get_folders", "send_email"]

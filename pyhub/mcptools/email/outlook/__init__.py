from pyhub.mcptools.core.choices import OS

if OS.current_is_windows():
    from pyhub.mcptools.email.outlook.win import *

# elif OS.current_is_macos():
#     from pyhub.mcptools.email.outlook.macos import *

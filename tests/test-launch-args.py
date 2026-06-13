# AI-hint: A test script for validating the `server._build_dispatch_cmd` logic by iterating through various app launch scenarios to verify that the correct command strings are generated for the agent-pipe.
# AI-related: /usr/lib/mios/agent-pipe
import sys, asyncio
sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server

cases = [
    ("launch_app", {"path": "/usr/bin/nautilus"}),
    ("launch_app", {"path": "/mnt/c/Windows/notepad.exe"}),
    ("launch_app", {"path": "/usr/share/applications/firefox.desktop"}),
    ("launch_app", {"name": "epiphany"}),
    ("launch_app", {"name": "mios_apps"}),   # defensive reject
    ("launch_app", {}),                       # no name+no path
    ("open_app",   {"path": "/usr/bin/code", "position": "left"}),
]
for tool, args in cases:
    cmd = server._build_dispatch_cmd(tool, args)
    print(f"  {tool}({args}) -> {cmd!r}")

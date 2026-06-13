# AI-hint: Validates the `server._build_dispatch_cmd` logic to ensure the dispatcher correctly filters and accepts/rejects specific application launch verbs and package names before execution.
# AI-related: /usr/lib/mios/agent-pipe, mios-apps
import sys
sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server

tests = [
    ("launch_app", {"name": "mios-apps"},                "REJECT (verb name)"),
    ("launch_app", {"name": "mios_apps"},                "REJECT (verb name)"),
    ("launch_app", {"name": "open_app"},                 "REJECT (verb name)"),
    ("launch_app", {"name": "tool_search"},              "REJECT (verb name)"),
    ("launch_app", {"name": "system_status"},            "REJECT (verb name)"),
    ("open_app",   {"name": "mios-apps"},                "REJECT (verb name)"),
    ("launch_app", {"name": "mobi.phosh.MobileSettings"}, "ACCEPT"),
    ("launch_app", {"name": "epiphany"},                 "ACCEPT"),
    ("launch_app", {"name": "Notepad"},                  "ACCEPT"),
]
for tool, args, expected in tests:
    out = server._build_dispatch_cmd(tool, args)
    status = "REJECT" if out is None else "ACCEPT"
    ok = "✓" if status == expected.split()[0] else "✗"
    print(f"  {ok} {tool}({args!r:50s}) -> {status:6s}  (expected {expected})")

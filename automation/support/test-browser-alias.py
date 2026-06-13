# AI-hint: Validates and debugs browser application configurations in mios.toml to verify launcher paths and default status for browser-role apps, used by agents to verify environment setup for web-based automation.
# AI-related: /usr/share/mios/mios.toml
import tomllib
with open("/usr/share/mios/mios.toml", "rb") as f:
    d = tomllib.load(f)
apps = d["desktop"]["apps"]
print(f"desktop.apps is {type(apps).__name__} len={len(apps)}")
browsers = [a for a in apps if a.get("role") == "browser"]
for a in browsers:
    flag = " (default)" if a.get("default") else ""
    print(f"  browser entry: {a.get('id')}{flag} launcher={a.get('launcher')!r}")
chromedev = next((a for a in apps if a.get("id") == "com.google.ChromeDev"), None)
print(f"chromedev.launcher = {chromedev.get('launcher') if chromedev else None!r}")

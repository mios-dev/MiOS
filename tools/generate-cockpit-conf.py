#!/usr/bin/env python3
# AI-hint: Renders etc/cockpit/cockpit.conf from usr/share/mios/mios.toml SSOT (AGY-165)
import os, sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ssot_path = os.path.join(root, "usr/share/mios/mios.toml")
    target_path = os.path.join(root, "etc/cockpit/cockpit.conf")
    check_mode = "--check" in sys.argv

    if not os.path.isfile(ssot_path):
        print(f"Error: SSOT file not found at {ssot_path}", file=sys.stderr)
        sys.exit(1)

    allow_unencrypted = "true"
    login_to = "false"
    idle_timeout = "0"

    if tomllib:
        try:
            with open(ssot_path, "rb") as f:
                data = tomllib.load(f)
            cockpit_cfg = data.get("cockpit", {})
            if "allow_unencrypted" in cockpit_cfg:
                allow_unencrypted = "true" if cockpit_cfg["allow_unencrypted"] else "false"
            if "login_to" in cockpit_cfg:
                login_to = "true" if cockpit_cfg["login_to"] else "false"
            if "idle_timeout" in cockpit_cfg:
                idle_timeout = str(cockpit_cfg["idle_timeout"])
        except Exception:
            pass

    rendered = f"""# Cockpit configuration file
# Generated from mios.toml -- DO NOT EDIT DIRECTLY
[WebService]
AllowUnencrypted = {allow_unencrypted}
LoginTo = {login_to}

[Session]
IdleTimeout = {idle_timeout}
"""

    if check_mode:
        if not os.path.isfile(target_path):
            print(f"Error: {target_path} does not exist", file=sys.stderr)
            sys.exit(1)
        with open(target_path, "r", encoding="utf-8") as f:
            current = f.read()
        if current.strip() != rendered.strip():
            print(f"Error: {target_path} is out of sync with mios.toml SSOT", file=sys.stderr)
            sys.exit(1)
        print("[OK] etc/cockpit/cockpit.conf is in sync with SSOT")
        sys.exit(0)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Generated {target_path}")

if __name__ == "__main__":
    main()

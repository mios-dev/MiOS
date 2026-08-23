#!/usr/bin/env python3
# AI-hint: Generates usr/share/applications/*.desktop files from SSOT ports and [desktop.launchers] table. Zero hardcoded port literals; --check is the drift gate.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_render_desktop_py.md
"""render-desktop.py -- render all .desktop launchers from mios.toml SSOT.

Usage:
    tools/render-desktop.py          # write rendered .desktop files
    tools/render-desktop.py --check  # exit 1 if any .desktop file has drifted
"""
from __future__ import annotations
import argparse
import os
import sys

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "usr/lib/mios"))

try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(1)


def load_ssot(root: str) -> tuple[dict, dict]:
    p = os.path.join(root, "usr/share/mios/mios.toml")
    with open(p, "rb") as fh:
        data = _toml.load(fh)
    ports = dict(data.get("ports") or {})
    desktop = dict((data.get("desktop") or {}).get("launchers") or {})
    return ports, desktop


def render_launcher(name: str, cfg: dict, ports: dict) -> str:
    port_key = cfg.get("port_key", "")
    port = ports.get(port_key) if port_key else None
    
    if "exec_cmd" in cfg:
        exec_cmd = cfg["exec_cmd"]
    elif port is not None:
        scheme = cfg.get("scheme", "http")
        path = cfg.get("path", "/")
        exec_cmd = f"xdg-open {scheme}://localhost:{port}{path}"
    else:
        exec_cmd = ""

    comment = cfg.get("comment", "")
    if port is not None:
        comment = comment.replace("{port}", str(port))
        
    ai_hint = cfg.get("ai_hint", "")
    if port is not None:
        ai_hint = ai_hint.replace("{port}", str(port))
        
    ai_related = cfg.get("ai_related", "")
    if not ai_related and port is not None:
        ai_related = f"localhost:{port}"

    lines = []
    if ai_hint:
        lines.append(f"# AI-hint: {ai_hint}")
    if ai_related:
        lines.append(f"# AI-related: {ai_related}")
    
    lines.append("[Desktop Entry]")
    lines.append("Type=Application")
    lines.append("Version=1.0")
    lines.append(f"Name={cfg.get('title', '')}")
    if "generic_name" in cfg:
        lines.append(f"GenericName={cfg['generic_name']}")
    if comment:
        lines.append(f"Comment={comment}")
    if exec_cmd:
        lines.append(f"Exec={exec_cmd}")
    if "icon" in cfg:
        lines.append(f"Icon={cfg['icon']}")
    if "categories" in cfg:
        lines.append(f"Categories={cfg['categories']}")
    if "keywords" in cfg:
        lines.append(f"Keywords={cfg['keywords']}")
    
    lines.append(f"Terminal={'true' if cfg.get('terminal', False) else 'false'}")
    lines.append(f"StartupNotify={'true' if cfg.get('startup_notify', True) else 'false'}")
    
    if "startup_wm_class" in cfg:
        lines.append(f"StartupWMClass={cfg['startup_wm_class']}")
    if "no_display" in cfg:
        lines.append(f"NoDisplay={'true' if cfg['no_display'] else 'false'}")
        
    if "trailing_comments" in cfg:
        lines.extend(cfg["trailing_comments"])

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(prog="render-desktop")
    ap.add_argument("--check", action="store_true", help="Exit 1 if any .desktop file has drifted")
    args = ap.parse_args()

    ports, launchers = load_ssot(ROOT)
    apps_dir = os.path.join(ROOT, "usr/share/applications")

    # An empty launcher table renders nothing, compares nothing, and reports
    # success -- which is how 9 shipped .desktop files stayed ungoverned while
    # this gate was green. If the tree ships launchers, SSOT must describe them.
    on_disk = sorted(f for f in os.listdir(apps_dir)
                     if f.endswith(".desktop")) if os.path.isdir(apps_dir) else []
    if not launchers:
        print("[render-desktop] mios.toml [desktop.launchers] is empty or absent, "
              "but %d .desktop file(s) ship in usr/share/applications. Nothing "
              "would be compared." % len(on_disk), file=sys.stderr)
        return 1
    unmanaged = [f for f in on_disk if f[:-8] not in launchers]
    if unmanaged and args.check:
        for f in unmanaged:
            print("[render-desktop] DRIFT: %s ships but no [desktop.launchers.%s] "
                  "declares it" % (f, f[:-8]), file=sys.stderr)
        return 1

    drifted = []
    for name, cfg in sorted(launchers.items()):
        rendered = render_launcher(name, cfg, ports)
        target_path = os.path.join(apps_dir, f"{name}.desktop")
        
        if args.check:
            if not os.path.isfile(target_path):
                drifted.append(f"{name}.desktop missing")
                continue
            with open(target_path, "r", encoding="utf-8") as fh:
                current = fh.read()
            if current != rendered:
                drifted.append(f"{name}.desktop content drifted")
        else:
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(rendered)

    if args.check:
        if drifted:
            for d in drifted:
                print(f"[render-desktop] DRIFT: {d}", file=sys.stderr)
            return 1
        print("[render-desktop] All .desktop launchers match SSOT", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

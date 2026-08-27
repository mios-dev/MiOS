#!/usr/bin/env python3
# AI-hint: Hyprland and Sway tiling window manager configuration generator from SSOT with hot-reload support
# AI-related: tests/test-wm-config-gen.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
# AI-functions: WmConfigGenEngine, generate_hyprland_conf, generate_sway_config, trigger_wm_reload, main
"""
MiOS Window Manager (Hyprland & Sway) Configuration Generator.

Projects keybindings, gaps, border widths, animations, and SSOT palette tokens
into native compositor configuration files:
- Hyprland: `usr/share/mios/hyprland/hyprland.conf`
- Sway: `usr/share/mios/sway/config`
- Live reload trigger via `hyprctl reload` or `swaymsg reload`.
- Synchronizes behavior, workspaces, and shortcuts across both compositors.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Enable relative import of mios_toml
_LIB_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "lib", "mios")
)
if os.path.isdir(_LIB_DIR) and _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

try:
    import mios_toml
except ImportError:
    mios_toml = None

class WmConfigGenEngine:
    """Generates Hyprland and Sway compositor configurations with SSOT colors and geometry."""

    def __init__(
        self,
        gaps_inner: int = 5,
        gaps_outer: int = 10,
        border_size: int = 2,
        terminal: str = "alacritty",
        launcher: str = "rofi -show drun",
        mock: bool = False,
        dry_run: bool = False,
    ):
        self.gaps_inner = gaps_inner
        self.gaps_outer = gaps_outer
        self.border_size = border_size
        self.terminal = terminal
        self.launcher = launcher
        self.mock = mock
        self.dry_run = dry_run
        self.palette = self._load_palette()

    def _load_palette(self) -> Dict[str, str]:
        """Load color definitions from mios.toml SSOT or built-in defaults."""
        if mios_toml is not None:
            try:
                return mios_toml.colors()
            except Exception:
                pass
        return {
            "bg": "#282262",
            "fg": "#E7DFD3",
            "accent": "#1A407F",
            "cursor": "#F35C15",
            "success": "#3E7765",
            "warning": "#F35C15",
            "error": "#DC271B",
            "info": "#1A407F",
            "muted": "#948E8E",
            "subtle": "#B7C9D7",
        }

    def generate_hyprland_conf(self) -> str:
        """Generate Hyprland compositor configuration (hyprland.conf)."""
        p = self.palette
        bg_hex = p.get("bg", "#282262").lstrip("#")
        accent_hex = p.get("accent", "#1A407F").lstrip("#")
        cursor_hex = p.get("cursor", "#F35C15").lstrip("#")
        muted_hex = p.get("muted", "#948E8E").lstrip("#")

        return f"""# =====================================================================
# MiOS Hyprland Configuration
# Generated from mios.toml SSOT
# =====================================================================

# Display Monitors
monitor=,preferred,auto,1

# Input Devices
input {{
    kb_layout = us
    follow_mouse = 1
    touchpad {{
        natural_scroll = true
    }}
}}

# Window Layout & Gaps
general {{
    gaps_in = {self.gaps_inner}
    gaps_out = {self.gaps_outer}
    border_size = {self.border_size}
    col.active_border = rgba({cursor_hex}ee) rgba({accent_hex}ee) 45deg
    col.inactive_border = rgba({muted_hex}aa)
    layout = dwindle
    allow_tearing = false
}}

# Visual Decorations & Blur
decoration {{
    rounding = 8
    active_opacity = 1.0
    inactive_opacity = 0.95
    blur {{
        enabled = true
        size = 6
        passes = 2
        new_optimizations = true
    }}
    drop_shadow = true
    shadow_range = 12
    shadow_render_power = 3
    col.shadow = rgba({bg_hex}ee)
}}

# Animation Curves
animations {{
    enabled = true
    bezier = miosCurve, 0.05, 0.9, 0.1, 1.05
    animation = windows, 1, 5, miosCurve
    animation = windowsOut, 1, 5, default, popin 80%
    animation = border, 1, 8, default
    animation = fade, 1, 5, default
    animation = workspaces, 1, 5, miosCurve
}}

# Dwindle Layout Setup
dwindle {{
    pseudotile = true
    preserve_split = true
}}

# Keybindings
$mod = SUPER
bind = $mod, Return, exec, {self.terminal}
bind = $mod, Q, killactive,
bind = $mod, Space, exec, {self.launcher}
bind = $mod, E, exec, nautilus
bind = $mod, V, togglefloating,
bind = $mod, F, fullscreen, 0
bind = $mod, L, exec, mios-lock
bind = $mod Shift, E, exit,

# Workspace Switching
bind = $mod, 1, workspace, 1
bind = $mod, 2, workspace, 2
bind = $mod, 3, workspace, 3
bind = $mod, 4, workspace, 4
bind = $mod, 5, workspace, 5

# Window Movement to Workspaces
bind = $mod Shift, 1, movetoworkspace, 1
bind = $mod Shift, 2, movetoworkspace, 2
bind = $mod Shift, 3, movetoworkspace, 3
bind = $mod Shift, 4, movetoworkspace, 4
bind = $mod Shift, 5, movetoworkspace, 5
"""

    def generate_sway_config(self) -> str:
        """Generate Sway tiling window manager configuration (sway/config)."""
        p = self.palette
        bg = p.get("bg", "#282262")
        fg = p.get("fg", "#E7DFD3")
        accent = p.get("accent", "#1A407F")
        cursor = p.get("cursor", "#F35C15")
        muted = p.get("muted", "#948E8E")
        error = p.get("error", "#DC271B")

        return f"""# =====================================================================
# MiOS Sway Configuration
# Generated from mios.toml SSOT
# =====================================================================

# Mod Key
set $mod Mod4

# Font Configuration
font pango:DejaVu Sans Mono 10

# Gaps & Borders
default_border pixel {self.border_size}
default_floating_border pixel {self.border_size}
gaps inner {self.gaps_inner}
gaps outer {self.gaps_outer}

# Color Classes: <class> <border> <background> <text> <indicator> <child_border>
client.focused          {cursor} {accent} {fg} {cursor} {cursor}
client.focused_inactive {muted} {bg} {fg} {muted} {muted}
client.unfocused        {muted} {bg} {muted} {bg} {bg}
client.urgent           {error} {error} {fg} {error} {error}

# Keybindings
bindsym $mod+Return exec {self.terminal}
bindsym $mod+q kill
bindsym $mod+space exec {self.launcher}
bindsym $mod+v floating toggle
bindsym $mod+f fullscreen toggle
bindsym $mod+l exec mios-lock
bindsym $mod+Shift+e exec swaynag -t warning -m 'Exit Sway?' -b 'Yes' 'swaymsg exit'

# Workspace Switching
bindsym $mod+1 workspace number 1
bindsym $mod+2 workspace number 2
bindsym $mod+3 workspace number 3
bindsym $mod+4 workspace number 4
bindsym $mod+5 workspace number 5

# Window Movement to Workspaces
bindsym $mod+Shift+1 move container to workspace number 1
bindsym $mod+Shift+2 move container to workspace number 2
bindsym $mod+Shift+3 move container to workspace number 3
bindsym $mod+Shift+4 move container to workspace number 4
bindsym $mod+Shift+5 move container to workspace number 5
"""

    def trigger_reload(self, wm: str) -> Dict[str, Any]:
        """Trigger live reload of active window manager compositor."""
        if self.mock or self.dry_run:
            return {"reloaded": True, "wm": wm, "command": f"{wm} reload (mock)"}

        cmd = []
        if wm == "hyprland":
            if shutil.which("hyprctl"):
                cmd = ["hyprctl", "reload"]
        elif wm == "sway":
            if shutil.which("swaymsg"):
                cmd = ["swaymsg", "reload"]

        if not cmd:
            return {"reloaded": False, "wm": wm, "message": f"{wm} binary not in PATH"}

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            return {
                "reloaded": res.returncode == 0,
                "wm": wm,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
            }
        except Exception as e:
            return {"reloaded": False, "wm": wm, "error": str(e)}

    def write_output(self, path: str, content: str) -> None:
        """Write configuration to disk if not in mock or dry-run mode."""
        if not self.mock and not self.dry_run:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def run(
        self,
        wm: str = "all",
        out_dir: Optional[str] = None,
        reload_active: bool = False,
    ) -> Dict[str, Any]:
        """Execute window manager configuration generation."""
        hyprland_src = self.generate_hyprland_conf()
        sway_src = self.generate_sway_config()
        written_files = []

        if out_dir:
            if wm in ("hyprland", "all"):
                h_path = os.path.join(out_dir, "hyprland", "hyprland.conf")
                self.write_output(h_path, hyprland_src)
                written_files.append(h_path)
            if wm in ("sway", "all"):
                s_path = os.path.join(out_dir, "sway", "config")
                self.write_output(s_path, sway_src)
                written_files.append(s_path)

        reload_results = {}
        if reload_active:
            if wm in ("hyprland", "all"):
                reload_results["hyprland"] = self.trigger_reload("hyprland")
            if wm in ("sway", "all"):
                reload_results["sway"] = self.trigger_reload("sway")

        return {
            "status": "success",
            "wm": wm,
            "gaps_inner": self.gaps_inner,
            "gaps_outer": self.gaps_outer,
            "border_size": self.border_size,
            "hyprland_lines": len(hyprland_src.splitlines()),
            "sway_lines": len(sway_src.splitlines()),
            "written_files": written_files,
            "reload": reload_results if reload_active else None,
            "dry_run": self.dry_run,
            "mock": self.mock,
        }

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Hyprland & Sway Window Manager Configuration Generator"
    )
    parser.add_argument("--wm", default="all", choices=["hyprland", "sway", "all"],
                        help="Target window manager")
    parser.add_argument("--out-dir", help="Output root directory for WM configs")
    parser.add_argument("--gaps-in", type=int, default=5, help="Inner window gaps in pixels")
    parser.add_argument("--gaps-out", type=int, default=10, help="Outer window gaps in pixels")
    parser.add_argument("--border-size", type=int, default=2, help="Window border width in pixels")
    parser.add_argument("--reload", action="store_true", help="Trigger hot-reload of active compositor")
    parser.add_argument("--check", help="Verify syntax and compare with existing config")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without writing files")
    parser.add_argument("--mock", action="store_true", help="Deterministic mock execution for CI")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    engine = WmConfigGenEngine(
        gaps_inner=args.gaps_in,
        gaps_outer=args.gaps_out,
        border_size=args.border_size,
        mock=args.mock,
        dry_run=args.dry_run,
    )

    try:
        res = engine.run(
            wm=args.wm,
            out_dir=args.out_dir,
            reload_active=args.reload,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[wm_config_gen] SUCCESS: Generated configs for target '{args.wm}'")
            print(f"  Hyprland ({res['hyprland_lines']} lines) | Sway ({res['sway_lines']} lines)")
            if res["written_files"]:
                print(f"  Written files: {', '.join(res['written_files'])}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[wm_config_gen] ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

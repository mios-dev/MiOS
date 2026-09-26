#!/usr/bin/env python3
# AI-hint: Terminal multiplexer tmux theme generator deriving active pane styles and status bar formatting from SSOT
# AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py, usr/share/mios/tmux/mios-theme.tmux.conf
# AI-functions: TmuxThemeEngine, generate_tmux_config, main
"""
MiOS Tmux Theme & Status Line Generator.

Projects canonical palette tokens and styling preferences from `mios.toml` [colors]
and [theme] directly into `.tmux.conf` syntax:
- Pane borders: active (`cursor`), inactive (`muted`).
- Status line: background (`bg`), foreground (`fg`), selection (`accent`).
- Powerline glyph transitions (``, ``, ``, ``).
- Dynamic session and host indicators.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

_TREE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
if os.path.join(_TREE, "usr", "lib", "mios") not in sys.path:
    sys.path.insert(0, os.path.join(_TREE, "usr", "lib", "mios"))
import mios_toml  # noqa: E402 -- required: the palette resolves through [colors]

# sourced by usr/share/mios/tmux/blink-mobile-keys.tmux.conf; rendered at bake by automation/65-bake-hyprland.sh
GOLDEN = "usr/share/mios/tmux/mios-theme.tmux.conf"

class TmuxThemeEngine:
    """Generates tmux configuration files projecting SSOT palette and layout styles."""

    def __init__(
        self,
        style: str = "rounded",
        status_position: str = "bottom",
        mock: bool = False,
        dry_run: bool = False,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.style = style
        self.status_position = status_position
        self.mock = mock
        self.dry_run = dry_run
        self.palette = mios_toml.colors(data)

    def generate_config(self) -> str:
        """Render complete .tmux.conf theme snippet."""
        p = self.palette
        bg = p["bg"]
        fg = p["fg"]
        accent = p["accent"]
        cursor = p["cursor"]
        muted = p["muted"]
        subtle = p["subtle"]
        success = p["success"]

        lines = [
            "# AI-hint: tmux theme rendered by tmux_theme.py from mios.toml [colors]; tmux has no outer padding",
            "# =====================================================================",
            "# MiOS Canonical Tmux Theme",
            f"# Generated from mios.toml SSOT (Style: {self.style})",
            "# =====================================================================",
            "",
            "# Status Bar Placement & Refresh Interval",
            "set -g status on",
            "set -g status-interval 2",
            f"set -g status-position {self.status_position}",
            f'set -g status-style "bg={bg},fg={fg}"',
            "",
            "# Window Status Alignment & Separation",
            "set -g status-justify left",
            'set -g window-status-separator ""',
            "",
            "# Terminal Capabilities & Extended Keys",
            'set -g default-terminal "tmux-256color"',
            'set -as terminal-features ",xterm*:RGB"',
            'set -as terminal-overrides ",xterm*:Tc"',
            "",
            "# Pane Borders",
            f'set -g pane-border-style "fg={muted}"',
            f'set -g pane-active-border-style "fg={cursor}"',
            "set -g pane-border-lines heavy",
            "",
            "# Selection & Copy Mode",
            f'set -g mode-style "bg={accent},fg={fg}"',
            "",
            "# Message & Command Prompt",
            f'set -g message-style "bg={accent},fg={fg}"',
            f'set -g message-command-style "bg={bg},fg={cursor}"',
            "",
        ]

        if self.style == "powerline":
            lines.extend([
                "# Powerline Segment Formatting",
                "set -g status-left-length 40",
                f'set -g status-left "#[fg={fg},bg={accent},bold] #S #[fg={accent},bg={bg},nobold] "',
                f'set -g window-status-format "#[fg={muted},bg={bg}] #I:#W "',
                f'set -g window-status-current-format "#[fg={bg},bg={accent}]#[fg={fg},bg={accent},bold] #I:#W #[fg={accent},bg={bg},nobold]"',
                "set -g status-right-length 80",
                f'set -g status-right "#[fg={accent},bg={bg}]#[fg={fg},bg={accent}] %Y-%m-%d %H:%M #[fg={cursor},bg={accent}]#[fg={bg},bg={cursor},bold] #H "',
            ])
        elif self.style == "rounded":
            lines.extend([
                "# Rounded Glyph Formatting & Oh-My-Posh Graphics",
                "set -g status-left-length 50",
                f'set -g status-left "#[fg={accent},bg={bg}]#[fg={fg},bg={accent},bold]  MiOS #[fg={accent},bg={success}]#[fg={bg},bg={success},bold]  #S #[fg={success},bg={bg}] "',
                f'set -g window-status-format "#[fg={muted},bg={bg}]  #I  #W  "',
                f'set -g window-status-current-format "#[fg={cursor},bg={bg}]#[fg={bg},bg={cursor},bold] #I  #W #[fg={cursor},bg={bg}]"',
                "set -g status-right-length 100",
                f'set -g status-right "#[fg={accent},bg={bg}]#[fg={fg},bg={accent}]  %H:%M #[fg={accent},bg={success}]#[fg={bg},bg={success},bold]  %Y-%m-%d #[fg={success},bg={cursor}]#[fg={bg},bg={cursor},bold]  #H #[fg={cursor},bg={bg}]"',
            ])
        else:  # minimal / plain
            lines.extend([
                "# Minimal Status Line Formatting",
                "set -g status-left-length 30",
                f'set -g status-left "#[fg={accent},bold][#S] "',
                f'set -g window-status-format "#[fg={muted}]#I:#W"',
                f'set -g window-status-current-format "#[fg={cursor},bold][#I:#W]"',
                "set -g status-right-length 60",
                f'set -g status-right "#[fg={subtle}]%Y-%m-%d %H:%M #[fg={fg},bold]#H"',
            ])

        lines.append("")
        return "\n".join(lines)

    def write_output(self, path: str, content: str) -> None:
        """Write content to disk if not in mock or dry-run mode."""
        if not self.mock and not self.dry_run:
            mios_toml.write_atomic(path, content)

    def run(self, out_path: Optional[str] = None) -> Dict[str, Any]:
        """Execute tmux theme generation pipeline."""
        config_src = self.generate_config()

        if out_path:
            self.write_output(out_path, config_src)

        return {
            "status": "success",
            "style": self.style,
            "status_position": self.status_position,
            "palette": self.palette,
            "config_lines": len(config_src.splitlines()),
            "output_path": out_path,
            "config_preview": "\n".join(config_src.splitlines()[:15]) + "\n...",
            "dry_run": self.dry_run,
            "mock": self.mock,
        }

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Tmux Theme & Status Line Generator"
    )
    parser.add_argument("--render", action="store_true", help="Render tmux configuration")
    parser.add_argument("--output", "--out", dest="out", help="Output path for tmux configuration file")
    parser.add_argument("--style", default="rounded", choices=["powerline", "rounded", "minimal"],
                        help="Visual styling format for status line segments")
    parser.add_argument("--position", default="bottom", choices=["bottom", "top"],
                        help="Status bar screen position")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without writing files")
    parser.add_argument("--mock", action="store_true", help="Deterministic mock execution for CI")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")
    fixture = parser.add_mutually_exclusive_group()
    fixture.add_argument("--check-fixture", metavar="ROOT", help=f"Diff ROOT/{GOLDEN} against the vendor-tier render")
    fixture.add_argument("--write-fixture", metavar="ROOT", help=f"Regenerate ROOT/{GOLDEN} from the vendor tier")

    args = parser.parse_args()
    if args.check_fixture or args.write_fixture:
        try:
            rendered = TmuxThemeEngine(mock=True, data=mios_toml.vendor_tree(_TREE)).generate_config()
            return mios_toml.golden_gate("tmux_theme", args.check_fixture or args.write_fixture,
                                         {GOLDEN: rendered}, write=bool(args.write_fixture))
        except (ValueError, OSError) as exc:
            print(f"[tmux_theme] ERROR: {exc}", file=sys.stderr)
            return 1

    engine = TmuxThemeEngine(
        style=args.style,
        status_position=args.position,
        mock=args.mock,
        dry_run=args.dry_run,
    )

    try:
        res = engine.run(out_path=args.out)

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[tmux_theme] SUCCESS: Generated tmux theme ({res['config_lines']} lines) style '{args.style}'")
            print(f"  Borders: active={res['palette'].get('cursor')}, inactive={res['palette'].get('muted')}")
            if res.get("output_path"):
                print(f"  Saved config: {res['output_path']}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[tmux_theme] ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

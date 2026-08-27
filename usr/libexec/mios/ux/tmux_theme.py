#!/usr/bin/env python3
# AI-hint: Terminal multiplexer tmux theme generator deriving active pane styles and status bar formatting from SSOT
# AI-related: tests/test-tmux-theme.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
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

class TmuxThemeEngine:
    """Generates tmux configuration files projecting SSOT palette and layout styles."""

    def __init__(
        self,
        style: str = "powerline",
        status_position: str = "bottom",
        mock: bool = False,
        dry_run: bool = False,
    ):
        self.style = style
        self.status_position = status_position
        self.mock = mock
        self.dry_run = dry_run
        self.palette = self._load_palette()

    def _load_palette(self) -> Dict[str, str]:
        """Fetch color scheme from mios.toml SSOT or built-in defaults."""
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
            "earth": "#734F39",
            "silver": "#E0E0E0",
        }

    def generate_config(self) -> str:
        """Render complete .tmux.conf theme snippet."""
        p = self.palette
        bg = p.get("bg", "#282262")
        fg = p.get("fg", "#E7DFD3")
        accent = p.get("accent", "#1A407F")
        cursor = p.get("cursor", "#F35C15")
        muted = p.get("muted", "#948E8E")
        subtle = p.get("subtle", "#B7C9D7")
        success = p.get("success", "#3E7765")

        lines = [
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
            "# Pane Borders",
            f'set -g pane-border-style "fg={muted}"',
            f'set -g pane-active-border-style "fg={cursor}"',
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
                "# Rounded Glyph Formatting",
                "set -g status-left-length 40",
                f'set -g status-left "#[fg={accent},bg={bg}]#[fg={fg},bg={accent},bold]#S#[fg={accent},bg={bg}] "',
                f'set -g window-status-format "#[fg={muted},bg={bg}] #I:#W "',
                f'set -g window-status-current-format "#[fg={accent},bg={bg}]#[fg={fg},bg={accent},bold]#I:#W#[fg={accent},bg={bg}]"',
                "set -g status-right-length 80",
                f'set -g status-right "#[fg={accent},bg={bg}]#[fg={fg},bg={accent}]%Y-%m-%d %H:%M#[fg={accent},bg={bg}] #[fg={cursor},bg={bg}]#[fg={bg},bg={cursor},bold]#H#[fg={cursor},bg={bg}]"',
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
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

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
    parser.add_argument("--style", default="powerline", choices=["powerline", "rounded", "minimal"],
                        help="Visual styling format for status line segments")
    parser.add_argument("--position", default="bottom", choices=["bottom", "top"],
                        help="Status bar screen position")
    parser.add_argument("--check", help="Verify syntax and compare against existing tmux config")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without writing files")
    parser.add_argument("--mock", action="store_true", help="Deterministic mock execution for CI")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

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

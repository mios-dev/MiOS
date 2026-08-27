#!/usr/bin/env python3
# AI-hint: Btop system monitor theme renderer mapping exact RGB hex colors from mios.toml [colors] SSOT.
# AI-related: tests/test-btop-theme.py, usr/share/mios/mios.toml, etc/btop/themes/mios.theme
# AI-functions: BtopThemeRenderer, main
"""
MiOS Btop System Monitor Theme Renderer (T-461).

Renders btop system monitor theme file (etc/btop/themes/mios.theme) directly
from the mios.toml [colors] SSOT palette.
Ensures terminal system monitoring visually harmonizes with the operating
system color scheme with exact RGB hex mappings.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "lib", "mios"))
if os.path.isdir(_LIB_PATH) and _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

try:
    import mios_toml
except ImportError:
    mios_toml = None


DEFAULT_THEME_PATH = "/etc/btop/themes/mios.theme"
HEX_COLOR_REGEX = re.compile(r"^#([0-9a-fA-F]{6})$")


class BtopThemeRenderer:
    """Renders and validates btop monitor themes mapped from SSOT palette colors."""

    def __init__(
        self,
        output_path: Optional[str] = None,
        mock: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        self.output_path = output_path or DEFAULT_THEME_PATH
        self.mock = mock
        self.dry_run = dry_run
        self.verbose = verbose

    def get_palette(self) -> Dict[str, str]:
        """Fetch resolved color dictionary from mios_toml."""
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
            "ansi_0_black": "#282262",
            "ansi_1_red": "#DC271B",
            "ansi_2_green": "#3E7765",
            "ansi_3_yellow": "#F35C15",
            "ansi_4_blue": "#1A407F",
            "ansi_5_magenta": "#734F39",
            "ansi_6_cyan": "#B7C9D7",
            "ansi_7_white": "#E7DFD3",
            "ansi_8_bright_black": "#948E8E",
            "ansi_9_bright_red": "#FF6B5C",
            "ansi_10_bright_green": "#5FAA8E",
            "ansi_11_bright_yellow": "#FF8540",
            "ansi_12_bright_blue": "#3D6BA8",
            "ansi_13_bright_magenta": "#9D7660",
            "ansi_14_bright_cyan": "#E0E0E0",
            "ansi_15_bright_white": "#FFFFFF",
        }

    def build_theme_mapping(self, palette: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Map btop theme keys to SSOT hex colors."""
        p = palette or self.get_palette()
        bg = p.get("bg", "#282262")
        fg = p.get("fg", "#E7DFD3")
        accent = p.get("accent", "#1A407F")
        cursor = p.get("cursor", "#F35C15")
        success = p.get("success", "#3E7765")
        warning = p.get("warning", "#F35C15")
        error = p.get("error", "#DC271B")
        muted = p.get("muted", "#948E8E")
        subtle = p.get("subtle", "#B7C9D7")
        cyan = p.get("ansi_12_bright_blue", "#3D6BA8")

        return {
            # Main UI
            "main_bg": bg,
            "main_fg": fg,
            "title": fg,
            "hi_fg": cursor,
            "selected_bg": accent,
            "selected_fg": fg,
            "inactive_fg": muted,
            "graph_text": subtle,
            "meter_bg": muted,
            "proc_misc": subtle,
            # Box outlines
            "cpu_box": accent,
            "mem_box": accent,
            "net_box": accent,
            "proc_box": accent,
            "div_line": muted,
            # Temperature gradient (Cool -> Warm -> Hot)
            "temp_start": success,
            "temp_mid": warning,
            "temp_end": error,
            # CPU gradient
            "cpu_start": success,
            "cpu_mid": warning,
            "cpu_end": error,
            # Memory gradients
            "free_start": success,
            "free_mid": subtle,
            "free_end": cyan,
            "cached_start": accent,
            "cached_mid": cyan,
            "cached_end": subtle,
            "available_start": success,
            "available_mid": subtle,
            "available_end": cyan,
            "used_start": warning,
            "used_mid": cursor,
            "used_end": error,
            # Network gradients
            "download_start": cyan,
            "download_mid": accent,
            "download_end": subtle,
            "upload_start": cursor,
            "upload_mid": warning,
            "upload_end": error,
            # Process meters
            "process_start": success,
            "process_mid": warning,
            "process_end": error,
        }

    def render_theme_text(self, palette: Optional[Dict[str, str]] = None) -> str:
        """Render standard btop .theme file content."""
        mapping = self.build_theme_mapping(palette)
        lines = [
            "# MiOS Btop System Monitor Theme",
            "# Generated automatically from mios.toml [colors] SSOT",
            "# Do NOT edit directly; regenerate using `usr/libexec/mios/ux/btop_theme.py`",
            "",
        ]
        for key, val in mapping.items():
            lines.append(f'theme[{key}]="{val}"')

        lines.append("")
        return "\n".join(lines)

    def validate_theme_content(self, content: str) -> Tuple[bool, List[str]]:
        """Validate syntax of btop theme text."""
        errors: List[str] = []
        found_keys: set[str] = set()

        for line_num, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r'^theme\[([a-zA-Z0-9_]+)\]\s*=\s*"([^"]+)"$', line)
            if not match:
                errors.append(f"Line {line_num}: Invalid syntax format: '{line}'")
                continue

            key, hex_val = match.group(1), match.group(2)
            found_keys.add(key)
            if not HEX_COLOR_REGEX.match(hex_val):
                errors.append(f"Line {line_num}: Invalid hex color '{hex_val}' for key '{key}'")

        required_keys = {"main_bg", "main_fg", "cpu_box", "mem_box", "temp_start", "cpu_start"}
        missing = required_keys - found_keys
        if missing:
            errors.append(f"Missing required btop theme keys: {sorted(missing)}")

        return len(errors) == 0, errors

    def render(self, out_path: Optional[str] = None) -> Dict[str, Any]:
        """Render theme and optionally write to output file."""
        target = out_path or self.output_path
        theme_text = self.render_theme_text()
        valid, errors = self.validate_theme_content(theme_text)

        if not valid:
            raise ValueError(f"Generated btop theme failed validation: {errors}")

        if not self.mock and not self.dry_run:
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(theme_text)

        return {
            "status": "success",
            "action": "render",
            "target": target,
            "theme_len": len(theme_text),
            "keys_count": len(self.build_theme_mapping()),
            "preview": theme_text,
            "dry_run": self.dry_run,
            "mock": self.mock,
        }

    def check(self, target_path: Optional[str] = None) -> Dict[str, Any]:
        """Check integrity of an existing btop theme file."""
        target = target_path or self.output_path
        if self.mock:
            theme_text = self.render_theme_text()
            valid, errors = self.validate_theme_content(theme_text)
            return {
                "status": "valid" if valid else "invalid",
                "path": target,
                "errors": errors,
                "mock": True,
            }

        if not os.path.exists(target):
            return {
                "status": "missing",
                "path": target,
                "error": "Theme file does not exist",
            }

        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            valid, errors = self.validate_theme_content(content)
            return {
                "status": "valid" if valid else "invalid",
                "path": target,
                "errors": errors,
            }
        except Exception as e:
            return {
                "status": "error",
                "path": target,
                "error": str(e),
            }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Btop System Monitor Theme Renderer (T-461)"
    )
    parser.add_argument("--render", action="store_true", help="Render and output btop theme")
    parser.add_argument("--out", help="Output file path for theme")
    parser.add_argument("--user", action="store_true", help="Target user directory (~/.config/btop/themes/mios.theme)")
    parser.add_argument("--check", help="Validate an existing btop theme file")
    parser.add_argument("--mock", action="store_true", help="Deterministic in-memory mock mode")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    parser.add_argument("--json", action="store_true", help="Emit output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    out_path = args.out
    if args.user and not out_path:
        home = os.path.expanduser("~")
        out_path = os.path.join(home, ".config", "btop", "themes", "mios.theme")

    renderer = BtopThemeRenderer(
        output_path=out_path,
        mock=args.mock,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        if args.check:
            result = renderer.check(args.check)
        else:
            result = renderer.render(out_path=out_path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result.get("status", "ok")
            target = result.get("target") or result.get("path", "default")
            print(f"[btop_theme] Status: {status} | Target: {target}")
            if "errors" in result and result["errors"]:
                for err in result["errors"]:
                    print(f"  ERROR: {err}", file=sys.stderr)
        return 0 if result.get("status") in ("success", "valid") else 1
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[btop_theme] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

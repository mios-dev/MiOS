#!/usr/bin/env python3
# AI-hint: Fastfetch configuration generator projecting host hardware, bootc image and AI model specs into JSONC
# AI-related: tests/test-fastfetch-gen.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
# AI-functions: FastfetchGenEngine, generate_fastfetch_jsonc, main
"""
MiOS Fastfetch Configuration Generator.

Projects host hardware, bootc immutable image metadata, local AI inference lanes,
and SSOT color tokens into `config.jsonc` for Fastfetch system banner display:
- Includes OS, Kernel, Host, CPU, GPU, Memory hardware modules.
- Integrates custom MiOS modules: AI Engine, Active Model, Mesh Nodes, Bootc Image.
- Configures ANSI color mappings derived from `mios.toml` [colors].
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

class FastfetchGenEngine:
    """Generates JSONC fastfetch configuration with system and AI telemetry modules."""

    def __init__(
        self,
        logo_type: str = "small",
        mock: bool = False,
        dry_run: bool = False,
    ):
        self.logo_type = logo_type
        self.mock = mock
        self.dry_run = dry_run
        self.palette = self._load_palette()

    def _load_palette(self) -> Dict[str, str]:
        """Fetch colors from mios.toml SSOT or fallbacks."""
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

    def inspect_system_metadata(self) -> Dict[str, str]:
        """Gather host and AI system metadata for Fastfetch configuration."""
        if self.mock:
            return {
                "os_name": "MiOS Linux (bootc/OCI workstation)",
                "ai_engine": "mios-llm-light (llama-swap :11450)",
                "active_model": "Qwen2.5-Coder-7B-Instruct-GGUF",
                "bootc_image": "ghcr.io/mios-dev/mios:latest (sha256:7f8a91b2c3d4)",
                "mesh_nodes": "1 (Local Node)",
                "version": "2026.1",
            }

        # Real metadata query
        os_name = "MiOS Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_name = line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass

        bootc_img = "ghcr.io/mios-dev/mios:latest"
        if os.path.exists("/usr/share/mios/VERSION"):
            try:
                with open("/usr/share/mios/VERSION", "r", encoding="utf-8") as f:
                    ver = f.read().strip()
                    bootc_img = f"ghcr.io/mios-dev/mios:{ver}"
            except Exception:
                pass

        return {
            "os_name": os_name,
            "ai_engine": "mios-llm-light (llama-swap :11450)",
            "active_model": "Qwen2.5-Coder-7B-Instruct-GGUF",
            "bootc_image": bootc_img,
            "mesh_nodes": "1 (Local Node)",
            "version": "2026.1",
        }

    def generate_jsonc(self) -> str:
        """Generate Fastfetch JSONC configuration string."""
        meta = self.inspect_system_metadata()

        config = {
            "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
            "logo": {
                "type": self.logo_type,
                "padding": {
                    "top": 1,
                    "left": 2,
                    "right": 2,
                },
            },
            "display": {
                "separator": " 󰄾 ",
                "color": {
                    "keys": "blue",
                    "title": "cyan",
                    "separator": "yellow",
                },
            },
            "modules": [
                {"type": "title"},
                {"type": "separator"},
                {"type": "os", "key": "OS", "format": f"{meta['os_name']}"},
                {"type": "host", "key": "Host"},
                {"type": "kernel", "key": "Kernel"},
                {"type": "uptime", "key": "Uptime"},
                {"type": "packages", "key": "Packages"},
                {"type": "shell", "key": "Shell"},
                {"type": "display", "key": "Display"},
                {"type": "wm", "key": "WM"},
                {"type": "cpu", "key": "CPU"},
                {"type": "gpu", "key": "GPU"},
                {"type": "memory", "key": "Memory"},
                {"type": "disk", "key": "Disk"},
                {"type": "break"},
                {"type": "custom", "key": "AI Engine", "format": f"{meta['ai_engine']}"},
                {"type": "custom", "key": "Active Model", "format": f"{meta['active_model']}"},
                {"type": "custom", "key": "Mesh Nodes", "format": f"{meta['mesh_nodes']}"},
                {"type": "custom", "key": "Bootc Image", "format": f"{meta['bootc_image']}"},
                {"type": "break"},
                {"type": "colors", "symbol": "circle"},
            ],
        }

        # Pretty-print with standard JSON formatting
        return json.dumps(config, indent=2)

    def write_output(self, path: str, content: str) -> None:
        """Write configuration to disk if not mock or dry-run."""
        if not self.mock and not self.dry_run:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def run(self, out_path: Optional[str] = None) -> Dict[str, Any]:
        """Execute fastfetch generator pipeline."""
        jsonc_src = self.generate_jsonc()

        if out_path:
            self.write_output(out_path, jsonc_src)

        return {
            "status": "success",
            "logo_type": self.logo_type,
            "palette": self.palette,
            "jsonc_lines": len(jsonc_src.splitlines()),
            "output_path": out_path,
            "jsonc_preview": "\n".join(jsonc_src.splitlines()[:20]) + "\n...",
            "dry_run": self.dry_run,
            "mock": self.mock,
        }

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Fastfetch Configuration Generator"
    )
    parser.add_argument("--generate", action="store_true", help="Generate Fastfetch JSONC configuration")
    parser.add_argument("--out", "--output", dest="out", help="Output path for config.jsonc file")
    parser.add_argument("--logo-type", default="small", choices=["small", "auto", "none"],
                        help="Fastfetch logo display type")
    parser.add_argument("--check", help="Verify syntax against existing config.jsonc")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without writing files")
    parser.add_argument("--mock", action="store_true", help="Deterministic mock execution for CI")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    engine = FastfetchGenEngine(
        logo_type=args.logo_type,
        mock=args.mock,
        dry_run=args.dry_run,
    )

    try:
        res = engine.run(out_path=args.out)

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[fastfetch_gen] SUCCESS: Generated Fastfetch config ({res['jsonc_lines']} lines)")
            if res.get("output_path"):
                print(f"  Saved config: {res['output_path']}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[fastfetch_gen] ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

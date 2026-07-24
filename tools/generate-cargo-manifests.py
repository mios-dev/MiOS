#!/usr/bin/env python3
# AI-hint: Generator that projects tools/native/Cargo.toml from mios.toml [meta].mios_version SSOT.
from __future__ import annotations

import os
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib/tomli not found", file=sys.stderr)
        sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOML_PATH = os.path.join(ROOT, "usr/share/mios/mios.toml")
VERSION_FILE = os.path.join(ROOT, "VERSION")


def get_ssot_version() -> str:
    if os.path.isfile(TOML_PATH):
        with open(TOML_PATH, "rb") as f:
            data = tomllib.load(f)
            v = data.get("meta", {}).get("mios_version")
            if v:
                return str(v)
    if os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "0.3.0"


def main() -> None:
    version = get_ssot_version()
    cargo_toml_path = os.path.join(ROOT, "tools", "native", "Cargo.toml")

    content = f"""# AI-hint: Generated from mios.toml SSOT by tools/generate-cargo-manifests.py. DO NOT EDIT DIRECTLY.
[workspace]
members = [
    "mios-version-check",
    "mios-wallpaperd",
    "generate-names-registry",
    "mios-ssot-walk",
    "mios-aiplane-lint",
]
resolver = "2"

[workspace.package]
version = "{version}"
edition = "2021"
"""

    with open(cargo_toml_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[generate-cargo-manifests] Projected tools/native/Cargo.toml with version {version} from SSOT")


if __name__ == "__main__":
    main()

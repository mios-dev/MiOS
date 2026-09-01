#!/usr/bin/env python3
# AI-hint: Generator that projects tools/native/Cargo.toml -- members enumerated from the crate directories, version from mios.toml [meta].mios_version SSOT.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Project tools/native/Cargo.toml. --check diffs instead of writing."""
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
NATIVE_DIR = os.path.join(ROOT, "tools", "native")
CARGO_TOML = os.path.join(NATIVE_DIR, "Cargo.toml")

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

def enumerate_members(native_dir: str) -> list[str]:
    """Every directory under native_dir holding a Cargo.toml, sorted."""
    if not os.path.isdir(native_dir):
        return []
    return sorted(
        name for name in os.listdir(native_dir)
        if os.path.isfile(os.path.join(native_dir, name, "Cargo.toml"))
    )

def render(members: list[str], version: str) -> str:
    listed = "".join(f'    "{m}",\n' for m in members)
    return (
        "# AI-hint: Generated from mios.toml SSOT by tools/generate-cargo-manifests.py. DO NOT EDIT DIRECTLY.\n"
        "[workspace]\n"
        "members = [\n"
        f"{listed}"
        "]\n"
        'resolver = "2"\n'
        "\n"
        "[workspace.package]\n"
        f'version = "{version}"\n'
        'edition = "2021"\n'
    )

def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    version = get_ssot_version()
    members = enumerate_members(NATIVE_DIR)
    # Emitting an empty workspace would silently retire every crate, so an
    # unreadable tools/native is a failure rather than a projection.
    if not members:
        print(f"[generate-cargo-manifests] FAIL: no crate directory under {NATIVE_DIR}, "
              "so the projection would empty the workspace", file=sys.stderr)
        return 1

    content = render(members, version)

    if check_mode:
        try:
            with open(CARGO_TOML, "r", encoding="utf-8") as f:
                committed = f.read()
        except OSError as exc:
            print(f"[generate-cargo-manifests] FAIL: cannot read {CARGO_TOML} ({exc})", file=sys.stderr)
            return 1
        if committed != content:
            print("[generate-cargo-manifests] FAIL: tools/native/Cargo.toml differs from its projection", file=sys.stderr)
            import difflib
            for line in difflib.unified_diff(committed.splitlines(True), content.splitlines(True),
                                             "committed", "projected"):
                sys.stderr.write("  " + line if line.endswith("\n") else "  " + line + "\n")
            return 1
        print(f"[generate-cargo-manifests] OK: tools/native/Cargo.toml matches its projection "
              f"({len(members)} member(s), version {version})")
        return 0

    with open(CARGO_TOML, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[generate-cargo-manifests] Projected tools/native/Cargo.toml with {len(members)} member(s) "
          f"and version {version} from SSOT")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

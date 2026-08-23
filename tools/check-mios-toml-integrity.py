#!/usr/bin/env python3
# AI-hint: Drift gate for mios.toml SSOT integrity, truncation, and table preservation (AGY-1682).
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: mios.toml parses as valid TOML, maintains min line count, and preserves top-level tables."""

import os
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

MIOS_TOML_RELATIVE = "usr/share/mios/mios.toml"
MIN_LINE_COUNT = 9000

# Required top-level tables that must always be present in mios.toml
REQUIRED_TOP_LEVEL_TABLES = {
    "versions",
    "security",
    "units",
    "unit_projection",
    "docs",
    "legibility",
    "ports",
}

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", os.environ.get("MIOS_TOML_ROOT", "."))
    path = os.path.join(root, MIOS_TOML_RELATIVE)
    if not os.path.isfile(path):
        print(f"VIOLATION: {MIOS_TOML_RELATIVE} not found under {root}")
        return 1

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    line_count = len(lines)
    if line_count < MIN_LINE_COUNT:
        print(
            f"VIOLATION: {MIOS_TOML_RELATIVE} line count ({line_count}) is below minimum baseline ({MIN_LINE_COUNT})"
        )
        return 1

    if tomllib is not None:
        try:
            parsed = tomllib.loads(content)
        except Exception as e:
            print(f"VIOLATION: {MIOS_TOML_RELATIVE} failed TOML parsing: {e}")
            return 1

        missing_tables = [table for table in REQUIRED_TOP_LEVEL_TABLES if table not in parsed]
        if missing_tables:
            print(
                f"VIOLATION: {MIOS_TOML_RELATIVE} is missing required top-level tables: {missing_tables}"
            )
            return 1
    else:
        # Fallback basic header check if tomllib/tomli unavailable
        found_tables = set()
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("[") and not line_str.startswith("[["):
                header = line_str.strip("[]").strip().split(".")[0]
                found_tables.add(header)
        missing_tables = [table for table in REQUIRED_TOP_LEVEL_TABLES if table not in found_tables]
        if missing_tables:
            print(
                f"VIOLATION: {MIOS_TOML_RELATIVE} is missing required top-level tables: {missing_tables}"
            )
            return 1

    print(f"mios.toml integrity check passed (lines={line_count})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

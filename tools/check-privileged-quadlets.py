#!/usr/bin/env python3
# AI-hint: Drift gate for privileged Quadlets register, justification, and ratchet ceiling (AGY-1651).
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: Privileged Quadlets register is minimal, ratcheted, and every entry justified."""

import os
import re
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

MIOS_TOML_RELATIVE = "usr/share/mios/mios.toml"

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", os.environ.get("MIOS_TOML_ROOT", "."))
    path = os.path.join(root, MIOS_TOML_RELATIVE)
    if not os.path.isfile(path):
        print(f"VIOLATION: {MIOS_TOML_RELATIVE} not found under {root}")
        return 1

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Extract [security.privileged_quadlets] block and check lines
    lines = content.splitlines()
    in_block = False
    in_root_array = False

    max_privileged_root = None
    root_entries = []

    for line in lines:
        line_clean = line.strip()
        if line_clean == "[security.privileged_quadlets]":
            in_block = True
            continue
        elif in_block and line_clean.startswith("["):
            in_block = False
            in_root_array = False

        if in_block:
            if line_clean.startswith("max_privileged_root"):
                parts = line_clean.split("=")
                if len(parts) == 2:
                    try:
                        max_privileged_root = int(parts[1].strip())
                    except ValueError:
                        pass
            elif line_clean.startswith("root = ["):
                in_root_array = True
                continue

            if in_root_array:
                if line_clean.startswith("]"):
                    in_root_array = False
                elif line_clean:
                    # e.g., "mios-ceph.container", # comment
                    m = re.search(r'"([^"]+\.container)"\s*,?\s*(#.*)?', line_clean)
                    if m:
                        unit_name = m.group(1)
                        comment = m.group(2)
                        root_entries.append((unit_name, comment))

    problems = []

    if max_privileged_root is None:
        problems.append("VIOLATION: [security.privileged_quadlets].max_privileged_root is not declared")
    else:
        actual_count = len(root_entries)
        if actual_count > max_privileged_root:
            problems.append(
                f"VIOLATION: privileged root count ({actual_count}) exceeds max_privileged_root ceiling ({max_privileged_root})"
            )

    for unit, comment in root_entries:
        if not comment or len(comment.strip("# ").strip()) < 5:
            problems.append(
                f"VIOLATION: privileged Quadlet '{unit}' lacks required capability justification comment"
            )

    if problems:
        for p in problems:
            print(p)
        return 1

    print(
        f"Privileged Quadlets register minimal & justified (entries={len(root_entries)}, max_ceiling={max_privileged_root})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Module-size ratchet for the agent-pipe extraction (drift check 149). Walks usr/lib/mios/agent-pipe/mios_pipe RECURSIVELY (the bash predecessor scanned find -maxdepth 1, so it certified "all modules <= 800 lines" while eleven files 820-1786 lines long sat one directory deeper). A file not in [refactor].oversize must be <= max_lines; a file that IS listed must be <= its recorded length and is reported when it shrinks, so the register can only ratchet down. Prints one line per violation and exits 1; prints a one-line summary and exits 0 when clean.
# AI-related: usr/share/mios/mios.toml [refactor], automation/98-drift-checks.sh, tools/test_check-module-length.py
# AI-functions: load_policy, scan, main
"""Shrink-only module-size ratchet for the agent-pipe extraction (check 149)."""

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

PKG = os.path.join("usr", "lib", "mios", "agent-pipe")
SUBDIR = "mios_pipe"


def load_policy(root: str) -> tuple:
    """Return (max_lines, {path: recorded_lines}) from [refactor]."""
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        data = tomllib.load(fh)
    sec = data.get("refactor") or {}
    max_lines = int(sec.get("max_lines") or 800)
    recorded = {}
    for row in sec.get("oversize") or []:
        if isinstance(row, dict) and row.get("path"):
            recorded[str(row["path"])] = int(row.get("lines") or 0)
    return max_lines, recorded


def _count(path: str) -> int:
    with open(path, "rb") as fh:
        return sum(1 for _ in fh)


def scan(root: str) -> tuple:
    """Return (violations, checked). A violation is a human-readable string."""
    max_lines, recorded = load_policy(root)
    base = os.path.join(root, PKG)
    top = os.path.join(base, SUBDIR)
    if not os.path.isdir(top):
        return [], 0
    seen = set()
    bad = []
    checked = 0
    for dirpath, _dirs, files in os.walk(top):
        for fn in sorted(files):
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            checked += 1
            n = _count(full)
            if rel in recorded:
                seen.add(rel)
                if n > recorded[rel]:
                    bad.append(
                        f"{rel} grew to {n} lines, above its recorded "
                        f"{recorded[rel]} -- the oversize register only ratchets DOWN")
                elif n < recorded[rel]:
                    bad.append(
                        f"{rel} is now {n} lines (recorded {recorded[rel]}) -- "
                        f"lower its [refactor].oversize entry to lock the win in")
            elif n > max_lines:
                bad.append(
                    f"{rel} is {n} lines, above the {max_lines}-line limit -- "
                    f"split it; do NOT add it to [refactor].oversize")
    for rel in sorted(set(recorded) - seen):
        bad.append(
            f"[refactor].oversize names a file that no longer exists: {rel}")
    return bad, checked


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    bad, checked = scan(root)
    if bad:
        for line in bad:
            print(line)
        return 1
    max_lines, recorded = load_policy(root)
    print(f"agent-pipe modules within the size ratchet "
          f"(checked={checked} limit={max_lines} grandfathered={len(recorded)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

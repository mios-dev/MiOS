# AI-hint: !/usr/bin/env python3 Module-size ratchet for the agent-pipe extraction (drift check 149).
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_check_module_length_py.md
"""Shrink-only module-size ratchet for the agent-pipe extraction (check 149)."""

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

PKG = os.path.join("usr", "lib", "mios", "agent-pipe")
# The whole agent-pipe tree, not just mios_pipe/: mios_dispatch.py (1178 lines)
# and server.py (4979) live at the ROOT and were outside every earlier version
# of this gate. Shims are excluded -- they are ~28 lines of lazy re-export.
SUBDIRS = ("mios_pipe", ".")


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


def _is_shim(path: str) -> bool:
    """A lazy re-export shim (~28 lines) is not a module worth sizing."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return "Re-export shim for" in fh.read(400)
    except OSError:
        return False


def _count(path: str) -> int:
    with open(path, "rb") as fh:
        return sum(1 for _ in fh)


def scan(root: str) -> tuple:
    """Return (violations, checked). A violation is a human-readable string."""
    max_lines, recorded = load_policy(root)
    base = os.path.join(root, PKG)
    if not os.path.isdir(base):
        return [], 0
    seen = set()
    bad = []
    checked = 0
    scanned = set()
    walked = []
    for sub in SUBDIRS:
        top = os.path.normpath(os.path.join(base, sub))
        if not os.path.isdir(top):
            continue
        if sub == ".":
            walked.append((top, sorted(os.listdir(top))))
        else:
            for dirpath, _dirs, files in os.walk(top):
                walked.append((dirpath, sorted(files)))
    for dirpath, files in walked:
        for fn in files:
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            full = os.path.join(dirpath, fn)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            if rel in scanned:
                continue
            scanned.add(rel)
            if _is_shim(full):
                continue
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

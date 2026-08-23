#!/usr/bin/env python3
# AI-hint: A utility script that uses regex to wrap the "MiOS" proper noun in single quotes in documentation and config files to ensure legal-attribution co...
# AI-doc: usr/share/doc/mios/manual/lib.md

import re, sys
from pathlib import Path

_LIT = "M" + "iOS"
PATTERN = re.compile(rf"(?<!['\w\"/\\]){_LIT}(?![-./\\\w'\"])")
REPLACE = f"'{_LIT}'"

ALLOW_EXT = {
    ".md", ".sh", ".ps1", ".py", ".toml", ".conf", ".service",
    ".target", ".container", ".preset", ".txt", ".rules", ".cfg",
}
ALLOW_NAMES = {"Containerfile", "Justfile"}

def is_allowed(path: Path) -> bool:
    if path.name in ALLOW_NAMES:
        return True
    if path.suffix in ALLOW_EXT:
        return True
    return False

def process(path: Path) -> int:
    """Return number of replacements made."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, IsADirectoryError, PermissionError):
        return 0
    new, n = PATTERN.subn(REPLACE, text)
    if n:
        path.write_text(new, encoding="utf-8")
    return n

if __name__ == "__main__":
    total_files = 0
    total_subs = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.is_file():
            continue
        if not is_allowed(p):
            continue
        n = process(p)
        if n:
            print(f"{n:4d}  {arg}")
            total_files += 1
            total_subs += n
    print(f"\n{total_subs} replacements across {total_files} files", file=sys.stderr)

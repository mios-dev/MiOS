#!/usr/bin/env python3
# AI-hint: Post-build build script that enforces Architectural Law 7 (OFFLINE-FIRST) by scanning the Hermes dashboard web dis...
# AI-doc: usr/share/doc/mios/manual/support.md
from __future__ import annotations
import re
import sys
import pathlib

PATTERN = re.compile(rb"https://fonts\.googleapis\.com/css2\?[^\"']+")
INERT = b"data:text/css,"

def main(dist_dir: str) -> int:
    dist = pathlib.Path(dist_dir)
    if not dist.is_dir():
        print(f"strip-externals: dist not a directory: {dist}", file=sys.stderr)
        return 1

    replaced = 0
    for f in dist.rglob("*"):
        if not f.is_file() or f.suffix not in {".js", ".css"}:
            continue
        raw = f.read_bytes()
        n = len(PATTERN.findall(raw))
        if n:
            f.write_bytes(PATTERN.sub(INERT, raw))
            print(f"  patched {f.relative_to(dist)}: {n} URL(s) -> data:text/css,")
            replaced += n

    remaining = 0
    for f in dist.rglob("*"):
        if not f.is_file() or f.suffix not in {".js", ".css", ".html"}:
            continue
        raw = f.read_bytes()
        for needle in (b"fonts.googleapis.com", b"fonts.gstatic.com"):
            c = raw.count(needle)
            if c:
                remaining += c
                print(f"  WARN: still found {needle.decode()} x{c} in {f.relative_to(dist)}", file=sys.stderr)

    print(f"strip-externals: {replaced} URL(s) replaced; {remaining} remaining")
    return 0 if remaining == 0 else 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <web_dist_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

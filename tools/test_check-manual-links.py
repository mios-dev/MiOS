#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-manual-links.py: builds throwaway manual trees in a temp dir and asserts the gate exits 0 on a clean T...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Fixture-driven checks that the manual link gate fails for the right reasons."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "check-manual-links.py")
FAILED = 0


def build(tmp, toc, chapters, extra=None):
    docs = os.path.join(tmp, "usr/share/doc/mios")
    os.makedirs(os.path.join(docs, "manual"), exist_ok=True)
    with open(os.path.join(docs, "manual.md"), "w", encoding="utf-8") as fh:
        fh.write(toc)
    for name, body in chapters.items():
        with open(os.path.join(docs, "manual", name), "w", encoding="utf-8") as fh:
            fh.write(body)
    for rel, body in (extra or {}).items():
        path = os.path.join(docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    return tmp


def run(root):
    env = dict(os.environ, MIOS_ROOT=root)
    return subprocess.run([sys.executable, GATE], env=env, capture_output=True, text=True).returncode


def case(name, toc, chapters, want_zero, extra=None):
    global FAILED
    with tempfile.TemporaryDirectory() as tmp:
        rc = run(build(tmp, toc, chapters, extra))
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} (exit {rc})")
    if not ok:
        FAILED += 1


CH = '<a name="01_intro"></a>\n# Chapter 01\n'

case("clean ToC resolves",
     "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": CH}, True)
case("dangling chapter link fails",
     "[Ch01](manual/ch01-missing.md#01_intro)\n", {"ch01-intro.md": CH}, False)
case("missing anchor fails",
     "[Ch01](manual/ch01-intro.md#not_there)\n", {"ch01-intro.md": CH}, False)
case("unreachable chapter fails",
     "[Ch01](manual/ch01-intro.md#01_intro)\n",
     {"ch01-intro.md": CH, "ch02-orphan.md": "# Chapter 02\n"}, False)
case("link without a fragment resolves",
     "[Ch01](manual/ch01-intro.md)\n", {"ch01-intro.md": CH}, True)

# The class that let audit-INDEX.md point at audit-mios-metal.md for the whole
# time after that name was reassigned to MiOS-Metal.
case("dangling ./sibling link fails",
     "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": CH}, False,
     extra={"reference/a.md": "see [b](./b.md)\n"})
case("resolving ./sibling link passes",
     "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": CH}, True,
     extra={"reference/a.md": "see [b](./b.md)\n", "reference/b.md": "# B\n"})
case("dangling ../parent link fails",
     "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": CH}, False,
     extra={"reference/a.md": "see [x](../concepts/x.md)\n"})
case("a repo-root-relative path is NOT this gate's business",
     "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": CH}, True,
     extra={"reference/a.md": "see [x](usr/share/mios/mios.toml)\n"})

print(f"\n{9 - FAILED}/9 checks pass")
sys.exit(1 if FAILED else 0)

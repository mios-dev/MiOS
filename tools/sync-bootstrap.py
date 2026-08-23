#!/usr/bin/env python3
# AI-hint: Law 15 repo sync. Mirrors the surfaces mios.toml [bootstrap.sync] declares from mios.git into mios-bootstrap.git, and mirrors the SSOT tables it ...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Keep mios-bootstrap.git in step with mios.git (Law 15).

Contract and rationale: installation/UNIFY.md.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def load_manifest(root: str) -> dict:
    with open(os.path.join(root, "usr", "share", "mios", "mios.toml"), "rb") as fh:
        data = tomllib.load(fh)
    return ((data.get("bootstrap") or {}).get("sync") or {}), data


def _norm(p: str) -> bytes:
    with open(p, "rb") as fh:
        return fh.read().replace(b"\r\n", b"\n")


def mirror_files(root: str, boot: str, files, apply: bool):
    """Returns the list of files that differ (before any copy)."""
    drift = []
    for rel in files:
        src = os.path.join(root, rel.replace("/", os.sep))
        dst = os.path.join(boot, rel.replace("/", os.sep))
        if not os.path.isfile(src):
            drift.append(f"{rel}: missing in mios.git (authority) -- remove it from "
                         f"[bootstrap.sync].mirror_files or restore it")
            continue
        if not os.path.isfile(dst) or _norm(src) != _norm(dst):
            drift.append(f"{rel}: differs")
            if apply:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
    return drift


def mirror_tables(root: str, boot: str, tables, data: dict, apply: bool):
    """Mirror whole [table] blocks into bootstrap's root mios.toml.

    Compares PARSED values, not text: bootstrap's file has its own comments and
    ordering, and a textual diff would report drift on every formatting choice.
    """
    drift = []
    bpath = os.path.join(boot, "mios.toml")
    if not os.path.isfile(bpath):
        return [f"bootstrap has no mios.toml at {bpath}"]
    with open(bpath, "rb") as fh:
        bdata = tomllib.load(fh)

    for table in tables:
        want = data.get(table) or {}
        got = bdata.get(table) or {}
        want_s = {k: v for k, v in want.items() if not isinstance(v, dict)}
        got_s = {k: v for k, v in got.items() if not isinstance(v, dict)}
        if want_s == got_s:
            continue
        for k in sorted(set(want_s) | set(got_s)):
            if want_s.get(k) != got_s.get(k):
                drift.append(f"[{table}].{k}: main={want_s.get(k)!r} bootstrap={got_s.get(k)!r}")
        if apply:
            _rewrite_table(bpath, table, want_s)
    return drift


def _rewrite_table(path: str, table: str, values: dict):
    """Replace the scalar keys of one [table] in place, preserving its comments."""
    src = io.open(path, encoding="utf-8", newline="").read()
    lines = src.splitlines(keepends=True)
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == f"[{table}]")
    except StopIteration:
        lines.append(f"\n[{table}]\n")
        start = len(lines) - 1
    end = start + 1
    while end < len(lines) and not lines[end].lstrip().startswith("["):
        end += 1

    KV = re.compile(r"^(\s*)([A-Za-z0-9_]+)(\s*=\s*)(.*)$")
    seen, out = set(), []
    for l in lines[start:end]:
        m = KV.match(l.rstrip("\n"))
        if not m or m.group(2) not in values:
            out.append(l)
            continue
        key = m.group(2)
        seen.add(key)
        out.append(f"{m.group(1)}{key}{m.group(3)}{_toml_val(values[key])}\n")
    for k in sorted(set(values) - seen):
        out.append(f"{k} = {_toml_val(values[k])}\n")
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        "".join(lines[:start] + out + lines[end:]))


def _toml_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_val(x) for x in v) + "]"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sync-bootstrap")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--bootstrap", default=os.environ.get("MIOS_BOOTSTRAP_ROOT")
                    or r"C:\mios-bootstrap")
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    ap.add_argument("--apply", action="store_true", help="write mios.git's copy into bootstrap")
    args = ap.parse_args(argv)

    man, data = load_manifest(args.root)
    if not man.get("mirror_files"):
        print("mios.toml [bootstrap.sync].mirror_files is empty or absent -- nothing "
              "would be compared, which is indistinguishable from being in sync",
              file=sys.stderr)
        return 1
    if not os.path.isdir(args.bootstrap):
        # Not an error in --check: a contributor need not have both repos.
        print(f"[sync-bootstrap] bootstrap repo not present at {args.bootstrap}; skipping")
        return 0

    drift = mirror_files(args.root, args.bootstrap, man["mirror_files"], args.apply)
    drift += mirror_tables(args.root, args.bootstrap,
                           man.get("mirror_toml_tables") or [], data, args.apply)

    if args.apply:
        print(f"[sync-bootstrap] applied {len(drift)} change(s) from mios.git")
        for d in drift:
            print(f"  {d}")
        return 0
    if drift:
        print(f"[sync-bootstrap] {len(drift)} surface(s) drifted from mios.git:",
              file=sys.stderr)
        for d in drift:
            print(f"  {d}", file=sys.stderr)
        return 1
    print(f"[sync-bootstrap] {len(man['mirror_files'])} mirrored file(s) and "
          f"{len(man.get('mirror_toml_tables') or [])} table(s) match mios.git")
    return 0


if __name__ == "__main__":
    sys.exit(main())

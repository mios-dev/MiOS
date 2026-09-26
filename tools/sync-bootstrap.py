#!/usr/bin/env python3
# AI-hint: Law 15 repo sync. Mirrors the surfaces mios.toml [bootstrap.sync] declares from mios.git into mios-bootstrap.git, and mirrors the SSOT tables it ...
# AI-doc: usr/share/doc/mios/manual/tools.md
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

def validate_manifest(man: dict) -> list[str]:
    """The manifest's own consistency, before anything is compared.

    unclassified_shared() unions mirror_files with not_mirrored, so a path in
    BOTH lists is invisible to it, and a padded entry names no file at all.
    """
    mirror = list(man.get("mirror_files") or ())
    notmir = list(man.get("not_mirrored") or ())
    bad = [f"{f}: declared in both [bootstrap.sync].mirror_files and .not_mirrored"
           for f in sorted(set(mirror) & set(notmir))]
    bad += [f"{f!r}: malformed [bootstrap.sync].mirror_files entry"
            for f in mirror if not f or f != f.strip()]
    bad += [f"{k!r}: malformed [bootstrap.sync].mirror_toml_keys entry (want \"<dotted.table>.<key>\")"
            for k in (man.get("mirror_toml_keys") or ()) if _split_key(k) is None]
    return bad

def _split_key(entry):
    """'theme.padding' -> ('theme', 'padding'); None when it names no table key."""
    if not isinstance(entry, str) or entry != entry.strip() or "." not in entry:
        return None
    table, key = entry.rsplit(".", 1)
    return (table, key) if table and key and "" not in table.split(".") else None

def _walk(data: dict, table: str):
    """Resolve a dotted table name through the nested tables; None when absent."""
    node = data
    for part in table.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node if isinstance(node, dict) else None

def _load_boot(boot: str):
    bpath = os.path.join(boot, "mios.toml")
    if not os.path.isfile(bpath):
        return bpath, None
    with open(bpath, "rb") as fh:
        return bpath, tomllib.load(fh)

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
        missing = not os.path.isfile(dst)
        if missing or _norm(src) != _norm(dst):
            drift.append(f"{rel}: missing in mios-bootstrap" if missing else f"{rel}: differs")
            if apply:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
    return drift

def mirror_tables(root: str, boot: str, tables, data: dict, apply: bool):
    """Mirror whole [table] blocks into bootstrap's root mios.toml.

    Compares PARSED values, not text: bootstrap's file has its own comments and
    ordering, and a textual diff would report drift on every formatting choice.
    """
    drift, fatal = [], []
    bpath, bdata = _load_boot(boot)
    if bdata is None:
        return [f"bootstrap has no mios.toml at {bpath}"], [bpath]

    for table in tables:
        want = _walk(data, table)
        if want is None:
            fatal.append(f"[{table}]: absent in mios.git")
            continue
        got = _walk(bdata, table) or {}
        want_s = {k: v for k, v in want.items() if not isinstance(v, dict)}
        got_s = {k: v for k, v in got.items() if not isinstance(v, dict)}
        if want_s == got_s:
            continue
        for k in sorted(set(want_s) | set(got_s)):
            if want_s.get(k) != got_s.get(k):
                drift.append(f"[{table}].{k}: main={want_s.get(k)!r} bootstrap={got_s.get(k)!r}")
        if apply:
            _rewrite_table(bpath, table, want_s)
    return drift + fatal, fatal

def mirror_keys(root: str, boot: str, keys, data: dict, apply: bool):
    """Mirror single "<dotted.table>.<key>" values; the rest of each table is repo-owned.

    Returns (drift, fatal): fatal is the drift --apply cannot repair.
    """
    drift, fatal = [], []
    if not keys:
        return drift, fatal
    bpath, bdata = _load_boot(boot)
    if bdata is None:
        return [f"bootstrap has no mios.toml at {bpath}"], [bpath]
    for entry in keys:
        table, key = _split_key(entry)
        want_t = _walk(data, table)
        if want_t is None or key not in want_t:
            fatal.append(f"[{table}]: absent in mios.git" if want_t is None
                         else f"[{table}].{key}: absent in mios.git")
            continue
        want = want_t[key]
        if isinstance(want, dict):
            fatal.append(f"[{table}].{key}: is a table in mios.git, not a key")
            continue
        got = (_walk(bdata, table) or {}).get(key)
        if want == got:
            continue
        drift.append(f"[{table}].{key}: main={want!r} bootstrap={got!r}")
        if apply:
            _rewrite_table(bpath, table, {key: want})
    return drift + fatal, fatal

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
    tmp = path + ".sync-tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("".join(lines[:start] + out + lines[end:]))
    shutil.copymode(path, tmp)
    os.replace(tmp, path)

def _toml_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_val(x) for x in v) + "]"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'

def unclassified_shared(root, boot, man):
    import subprocess

    def tracked(r):
        # check=False let a refused git empty `shared`, retiring this
        # direction silently. See ec94d4f3.
        p = subprocess.run(["git", "-C", r, "ls-files"],
                           capture_output=True, text=True, check=False)
        if p.returncode != 0:
            raise RuntimeError("git ls-files failed in %s (exit %d): %s"
                               % (r, p.returncode, (p.stderr or "").strip()))
        names = {l.strip().replace(os.sep, "/")
                 for l in p.stdout.splitlines() if l.strip()}
        if not names:
            raise RuntimeError("git ls-files listed no tracked file in %s, so no "
                               "undeclared shared file could be found" % r)
        return names

    declared = set(man.get("mirror_files") or ()) | set(man.get("not_mirrored") or ())
    try:
        shared = tracked(root) & tracked(boot)
    except RuntimeError as exc:
        return ["the undeclared-shared-file scan did not run: %s" % exc]
    return [f"{f}: tracked in both repos but declared in neither "
            f"[bootstrap.sync].mirror_files nor .not_mirrored"
            for f in sorted(shared - declared)]

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sync-bootstrap")
    ap.add_argument("--root", default=ROOT)
    _sib = os.path.join(os.path.dirname(ROOT), "mios-bootstrap")  # T-1033: the layout the absence message tells you to create
    ap.add_argument("--bootstrap", default=os.environ.get("MIOS_BOOTSTRAP_ROOT") or (_sib if os.path.isdir(_sib) else r"C:\mios-bootstrap"))
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    ap.add_argument("--apply", action="store_true", help="write mios.git's copy into bootstrap")
    args = ap.parse_args(argv)

    man, data = load_manifest(args.root)
    if not man.get("mirror_files"):
        print("mios.toml [bootstrap.sync].mirror_files is empty or absent -- nothing "
              "would be compared, which is indistinguishable from being in sync",
              file=sys.stderr)
        return 1
    bad = validate_manifest(man)
    if bad:
        print("[sync-bootstrap] mios.toml [bootstrap.sync] is inconsistent:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1
    if not os.path.isdir(args.bootstrap):
        # Absence is a failure, never a skip, with or without
        # MIOS_DRIFT_REQUIRE_TOOLS: a skip reports the same green as a run that
        # compared the two repos, and that is how they drifted while this passed.
        print(f"bootstrap repo absent at {args.bootstrap}: Law 15 NOT checked. Clone "
              f"mios-bootstrap beside this checkout, or set MIOS_BOOTSTRAP_ROOT",
              file=sys.stderr)
        return 1

    drift = unclassified_shared(args.root, args.bootstrap, man) if not args.apply else []
    drift += mirror_files(args.root, args.bootstrap, man["mirror_files"], args.apply)
    tdrift, tfatal = mirror_tables(args.root, args.bootstrap,
                                   man.get("mirror_toml_tables") or [], data, args.apply)
    keys = man.get("mirror_toml_keys") or []
    kdrift, kfatal = mirror_keys(args.root, args.bootstrap, keys, data, args.apply)
    drift += tdrift + kdrift

    if args.apply:
        fatal = tfatal + kfatal
        print(f"[sync-bootstrap] applied {len(drift) - len(fatal)} change(s) from mios.git")
        for d in drift:
            if d not in fatal:
                print(f"  {d}")
        if fatal:
            print(f"[sync-bootstrap] {len(fatal)} surface(s) --apply cannot repair:",
                  file=sys.stderr)
            for d in fatal:
                print(f"  {d}", file=sys.stderr)
            return 1
        return 0
    if drift:
        print(f"[sync-bootstrap] {len(drift)} surface(s) drifted from mios.git:",
              file=sys.stderr)
        for d in drift:
            print(f"  {d}", file=sys.stderr)
        return 1
    print(f"[sync-bootstrap] {len(man['mirror_files'])} mirrored file(s), "
          f"{len(man.get('mirror_toml_tables') or [])} table(s) and "
          f"{len(keys)} key(s) match mios.git")
    return 0

if __name__ == "__main__":
    sys.exit(main())

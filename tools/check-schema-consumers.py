#!/usr/bin/env python3
# AI-hint: Drift gate for dead schema. Every table in usr/share/mios/postgres/schema-init.sql must have at least one non-doc consumer in the tree --...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: no schema table is dead (no reader, no writer, not registered)."""

import os
import re
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

SCHEMA = "usr/share/mios/postgres/schema-init.sql"
# Doc, generated and CONFIG surfaces MENTION a table without consuming it. A
# .toml in particular declares policy about a table ([security.redact].tables,
# this gate's own register) -- naming it there is not reading or writing it, and
# counting it would let the register satisfy itself.
NON_CONSUMER_SUFFIXES = (".md", ".txt", ".tsv", ".json", ".snap", ".toml")
NON_CONSUMER_DIRS = ("/docs/", "usr/share/doc/", "usr/share/mios/reference/")
# A file GENERATED from mios.toml re-emits whatever the SSOT says -- including
# this gate's own register -- so a table name appearing there is an echo, not a
# consumer. Detected by the marker the renderers stamp, so a new projection is
# excluded automatically.
GENERATED_MARKER = "GENERATED IN FULL from usr/share/mios/mios.toml"


def declared_tables(root: str) -> list:
    path = os.path.join(root, SCHEMA)
    if not os.path.isfile(path):
        return []
    sql = open(path, encoding="utf-8", errors="replace").read()
    seen, out = set(), []
    for m in re.finditer(r'CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([A-Za-z0-9_."]+)\s*\(',
                         sql, re.I):
        name = m.group(1).strip('"')
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def has_consumer(root: str, table: str) -> bool:
    """True when some non-doc file outside the schema itself names the table."""
    short = table.split(".")[-1]
    try:
        r = subprocess.run(["git", "-C", root, "grep", "-l", "--", short],
                           capture_output=True, text=True)
    except OSError:
        return True          # no git: cannot judge, so do not accuse
    for f in r.stdout.split():
        if f == SCHEMA:
            continue
        if f.endswith(NON_CONSUMER_SUFFIXES):
            continue
        if any(d in f for d in NON_CONSUMER_DIRS):
            continue
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                if GENERATED_MARKER in fh.read(4096):
                    continue
        except OSError:
            pass
        return True
    return False


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        cfg = tomllib.load(fh)
    reg = (cfg.get("schema") or {}).get("unconsumed") or []
    registered = {}
    for row in reg:
        if isinstance(row, dict) and row.get("table"):
            registered[str(row["table"])] = str(row.get("reason") or "")

    tables = declared_tables(root)
    if not tables:
        print("schema-init.sql declares no tables (partial checkout)")
        return 0

    bad, live_registered = [], set()
    for t in tables:
        consumed = has_consumer(root, t)
        if t in registered:
            if consumed:
                bad.append(f"{t} is in [schema].unconsumed but now HAS a consumer "
                           f"-- remove its entry; the register only shrinks")
            else:
                live_registered.add(t)
        elif not consumed:
            bad.append(f"{t} has no reader and no writer anywhere -- wire it, drop "
                       f"it, or record it in [schema].unconsumed with a reason")
    for t in sorted(set(registered) - set(tables)):
        bad.append(f"[schema].unconsumed names {t}, which schema-init.sql no "
                   f"longer declares -- drop the entry")

    if bad:
        for line in bad:
            print(line)
        return 1
    print(f"every schema table has a consumer "
          f"(tables={len(tables)} registered-unconsumed={len(live_registered)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

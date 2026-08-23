#!/usr/bin/env python3
# AI-hint: DURA-02 persist-redaction coverage gate: asserts every table in postgres/schema-init.sql is classified in exactly one of [security.redact]...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Fail if a pgvector table is neither redacted nor explicitly exempt on persist."""
import os
import re
import sys
import tomllib

ROOT = os.environ.get("MIOS_ROOT", ".")
SSOT = os.path.join(ROOT, "usr/share/mios/mios.toml")
SCHEMA = os.path.join(ROOT, "usr/share/mios/postgres/schema-init.sql")
PG = os.path.join(ROOT, "usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py")
# Free-text agent surfaces that must never drop off the redact side.
MUST_REDACT = {"knowledge", "agent_memory", "event", "tool_call", "scratch"}


def main() -> int:
    cfg = (tomllib.load(open(SSOT, "rb")).get("security", {}) or {}).get("redact", {}) or {}
    tables = set(cfg.get("tables", []))
    exempt = set(cfg.get("exempt", []))
    schema = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?([a-z_]+)",
                            open(SCHEMA, encoding="utf-8").read()))
    bad = []
    for t in sorted(schema - tables - exempt):
        bad.append(f"schema table classified in NEITHER redact nor exempt: {t}")
    for t in sorted(tables & exempt):
        bad.append(f"table classified in BOTH redact and exempt: {t}")
    for t in sorted((tables | exempt) - schema):
        bad.append(f"classified table absent from the schema: {t}")
    for t in sorted(MUST_REDACT - tables):
        bad.append(f"free-text agent table must stay redacted: {t}")
    if os.path.isfile(PG):
        src = open(PG, encoding="utf-8").read()
        # Only the REDACTION site: an unrelated ("knowledge", "agent_memory")
        # tuple (the embedding-version check) is not this defect.
        if re.search(r'for t in \(\s*"knowledge"', src):
            bad.append("memory/pg.py still hardcodes its redaction table tuple")
        if "_redact_cfg" not in src:
            bad.append("memory/pg.py does not read [security.redact] from the SSOT")
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    print(f"persist redaction covers the schema "
          f"({len(tables)} redacted, {len(exempt)} exempt, {len(schema)} tables)")
    return 0


sys.exit(main())

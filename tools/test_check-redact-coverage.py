#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-redact-coverage.py: builds throwaway schema/SSOT/pg.py trees and asserts the gate passes a fully cl...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Assert the persist-redaction coverage gate fails for each defect class."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "check-redact-coverage.py")
FAILED = 0

SCHEMA = ("CREATE TABLE IF NOT EXISTS knowledge (id int);\n"
          "CREATE TABLE IF NOT EXISTS agent_memory (id int);\n"
          "CREATE TABLE IF NOT EXISTS event (id int);\n"
          "CREATE TABLE IF NOT EXISTS tool_call (id int);\n"
          "CREATE TABLE IF NOT EXISTS scratch (id int);\n"
          "CREATE TABLE IF NOT EXISTS agent_keypair (id int);\n")
GOOD_TOML = ('[security.redact]\nenable = true\nfail_closed = true\n'
             'tables = ["knowledge", "agent_memory", "event", "tool_call", "scratch"]\n'
             'exempt = ["agent_keypair"]\n')
GOOD_PG = "def _redact_cfg():\n    return {}\n"


def build(tmp, schema=SCHEMA, toml=GOOD_TOML, pg=GOOD_PG):
    os.makedirs(os.path.join(tmp, "usr/share/mios/postgres"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/memory"), exist_ok=True)
    open(os.path.join(tmp, "usr/share/mios/postgres/schema-init.sql"), "w").write(schema)
    open(os.path.join(tmp, "usr/share/mios/mios.toml"), "w").write(toml)
    open(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py"), "w").write(pg)
    return tmp


def case(label, want_zero, **kw):
    global FAILED
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, MIOS_ROOT=build(tmp, **kw))
        rc = subprocess.run([sys.executable, GATE], env=env,
                            capture_output=True, text=True).returncode
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit {rc})")
    if not ok:
        FAILED += 1


case("fully classified schema passes", True)
case("unclassified new table fails", False,
     schema=SCHEMA + "CREATE TABLE IF NOT EXISTS brand_new_sink (id int);\n")
case("table in BOTH lists fails", False,
     toml=GOOD_TOML.replace('exempt = ["agent_keypair"]',
                            'exempt = ["agent_keypair", "scratch"]'))
case("classified table absent from schema fails", False,
     toml=GOOD_TOML.replace('exempt = ["agent_keypair"]',
                            'exempt = ["agent_keypair", "ghost_table"]'))
case("free-text table dropped from redact fails", False,
     toml=GOOD_TOML.replace('"tool_call", "scratch"]', '"tool_call"]')
                  .replace('exempt = ["agent_keypair"]',
                           'exempt = ["agent_keypair", "scratch"]'))
case("pg.py hardcoding its tuple fails", False,
     pg='if params and any(t in sql.lower() for t in ("knowledge", "agent_memory")):\n')
case("pg.py ignoring the SSOT fails", False, pg="def something_else():\n    pass\n")
case("unrelated embedding tuple is not the defect", True,
     pg=GOOD_PG + 'if emb_version and table in ("knowledge", "agent_memory"):\n    pass\n')

print(f"\n{8 - FAILED}/8 checks pass")
sys.exit(1 if FAILED else 0)

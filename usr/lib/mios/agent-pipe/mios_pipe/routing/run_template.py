# AI-hint: WS-6 run-template CAPTURE + the T-225 replay source, extracted out of dag_exec so the two halves of one feature live together. Owns the structural plan-shape class (_run_template_class -- computable only AFTER planning), the fire-and-forget capture that now also records the TURN's intent key (the question you can ask BEFORE planning), and load_run_templates, the newest-first reader the planner's replay matcher consults. Every DB helper and the RUN_TEMPLATE_ENABLE flag arrive by one-way injection through configure(); this module NEVER imports server or dag_exec. dag_exec re-exports all three names so server.py's imports are unchanged.
# AI-related: ./replay.py, ./dag_exec.py, ./planner.py, /usr/share/mios/postgres/schema-init.sql, ./test_mios_run_template.py
# AI-functions: configure, _run_template_class, load_run_templates, _capture_run_template
"""Run-template capture + the replay read side (WS-6 / T-225)."""

from __future__ import annotations

import hashlib
from typing import Optional

from mios_pipe.routing import replay as _replay   # T-225 intent keying

RUN_TEMPLATE_ENABLE = True
_PG_PRIMARY = False
_db_read = None
_db_create = None
_db_post = None
_db_fire = None
_pg_mirror = None


def configure(*, run_template_enable=None, pg_primary=None, db_read=None,
              db_create=None, db_post=None, db_fire=None, pg_mirror=None) -> None:
    """One-way injection from dag_exec's own configure()."""
    global RUN_TEMPLATE_ENABLE, _PG_PRIMARY
    global _db_read, _db_create, _db_post, _db_fire, _pg_mirror
    if run_template_enable is not None:
        RUN_TEMPLATE_ENABLE = bool(run_template_enable)
    if pg_primary is not None:
        _PG_PRIMARY = bool(pg_primary)
    if db_read is not None:
        _db_read = db_read
    if db_create is not None:
        _db_create = db_create
    if db_post is not None:
        _db_post = db_post
    if db_fire is not None:
        _db_fire = db_fire
    if pg_mirror is not None:
        _pg_mirror = pg_mirror


def _run_template_class(dag: dict) -> str:
    """Structural intent-class key for a DAG: sorted tool/agent names + total
    edge count, hashed. Same plan SHAPE -> same class regardless of phrasing."""
    nodes = dag.get("nodes") or []
    sig = sorted(str(n.get("tool") or n.get("agent") or "?") for n in nodes)
    edges = sum(len(n.get("deps") or []) for n in nodes)
    raw = "|".join(sig) + f"#e{edges}"
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]


async def load_run_templates(limit: int = 50) -> list:
    """Newest stored templates for the replay matcher. Degrades open."""
    if not RUN_TEMPLATE_ENABLE or _db_read is None:
        return []
    n = max(1, int(limit or 50))
    sql = ("SELECT intent, intent_key, dag, class, ts FROM run_template "
           f"WHERE intent_key IS NOT NULL AND intent_key <> '' ORDER BY ts DESC LIMIT {n}")
    try:
        resp = await _db_read(sql + ";", pg_sql=sql)
    except Exception:  # noqa: BLE001 -- degrade-open: a read failure just means planning
        return []
    for st in (resp or []):
        if isinstance(st, dict) and isinstance(st.get("result"), list):
            return st["result"]
    return []


def _capture_run_template(dag: dict, session_id: Optional[str]) -> None:
    """Fire-and-forget capture of a planned DAG as a replayable template. Never
    raises (degrade-open) -- capture must not affect the run."""
    if not RUN_TEMPLATE_ENABLE:
        return
    try:
        nodes = dag.get("nodes") or []
        if not nodes:
            return
        _intent = str(dag.get("intent") or "")[:2000]
        _row = {
            "class": _run_template_class(dag),
            "summary": str(dag.get("summary") or "")[:500],
            "node_count": len(nodes),
            "dag": dag,
            "intent": _intent,
            "intent_key": _replay.intent_key(_intent),
        }
        _pg_mirror("run_template", dict(_row, session_id=session_id))  # WS-9c
        sql = _db_create("run_template", _row, now_fields=("ts",), _mirror=False)
        if session_id:
            sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
        if not _PG_PRIMARY:                      # WS-9c: pgvector mirror is primary
            _db_fire(_db_post(sql))
    except Exception:  # noqa: BLE001
        pass


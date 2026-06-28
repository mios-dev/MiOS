# AI-hint: ADVERTISED-SURFACE / capability + read-only admin route-handler LOGIC extracted VERBATIM from server.py (refactor R-CAPS wave). Owns the *_logic bodies behind the discovery + introspection endpoints: the verb catalog projections (/v1/verbs MCP-shape, /v1/verbs/openai-tools, the unified /v1/tools superset), the MCP Resource surface (/v1/resources list + /v1/resources/read, with the moved _skill_to_mcp_resource/_recipe_to_mcp_resource/_verb_to_mcp_resource projectors), the RBAC-filtered capability manifest + DAG (/v1/capabilities, /v1/capabilities/dag), the gossip peer digest (/v1/peers), the kernel Router shadow (/v1/route), the cost ledger (/v1/cost), the trace ring-buffer reads (/v1/trace + /v1/trace/{id}), the offline posture (/v1/offline-status), the skill catalog surface (/skills/list|show|run|openai-tools), the KG lookup (/kg/lookup), the DCI surface (/dci/deliberate + /dci/schema), and the /v1/models + /v1/embeddings proxy bodies. Moved byte-identically -- the @app routes stay THIN in server.py calling these via sys.modules so the HTTP + importable surface is unchanged. mios_capreg + the DCI act vocabulary are imported directly; every server-resident dep (the _VERB_CATALOG, _A2A_PEERS registry + lock, _KERNEL, the cost ledger/model + flags, the tracer, BACKEND, and the helper callables _verb_to_openai_tool/_recipe_to_openai_tool/_skill_to_openai_tool/_load_recipe_catalog/_skill_list/_skill_fetch/_user_rbac_filter/_match_user_cfg/_toml_section/_cap_skills/_get_client/kg_lookup/execute_skill/run_dci_flow/_offline_posture) is dependency-INJECTED via configure(). This module NEVER imports server. The cluster-health/scheduler/health handlers are deliberately NOT moved here (they reference the runtime-REASSIGNED _LANE_RESOLVER global, unsafe to inject by value).
# AI-related: ./server.py, ./mios_config.py, ./mios_capreg.py, ./mios_dci.py, ./test_mios_http_caps.py
# AI-functions: list_verbs_logic, list_verbs_openai_tools_logic, list_tools_logic, list_resources_logic, read_resource_logic, v1_capabilities_logic, v1_capabilities_dag_logic, v1_peers_logic, v1_route_logic, cost_ledger_logic, trace_read_logic, trace_recent_logic, offline_status_logic, prompt_registry_view_logic, run_templates_list_logic, list_models_logic, embeddings_logic, kg_lookup_endpoint_logic, skills_list_logic, skills_show_logic, skills_run_logic, skills_openai_tools_logic, dci_deliberate_logic, dci_schema_logic, _skill_to_mcp_resource, _recipe_to_mcp_resource, _verb_to_mcp_resource, configure
"""Advertised-surface / capability + read-only admin route-handler logic (refactor R-CAPS).

Extracted VERBATIM from ``server.py``: the bodies behind the discovery and
introspection endpoints (verb/tool/resource projections, the RBAC-filtered
capability manifest + DAG, the gossip peer digest, the kernel Router shadow, the
cost ledger, the trace ring-buffer reads, the offline posture, the skill catalog,
the KG lookup, the DCI surface, and the ``/v1/models`` + ``/v1/embeddings``
proxies). Each handler body is moved byte-identically into a ``*_logic`` function;
the ``@app`` routes stay in ``server.py`` as thin wrappers calling these via
``sys.modules`` so the HTTP + importable surface is unchanged.

``mios_capreg`` and the DCI act vocabulary are imported directly; every
server-resident dependency is injected via :func:`configure` (one-way boundary --
this module never imports ``server``). The three MCP Resource projectors
(``_skill_to_mcp_resource`` / ``_recipe_to_mcp_resource`` / ``_verb_to_mcp_resource``)
are moved here in full and re-imported by ``server.py`` under their original names.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import mios_capreg
from mios_dci import (
    DCI_ENABLED,
    _DCI_ACTS,
    _DCI_ACT_NAMES,
    _DCI_ACT_SCHEMA,
)

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# Every server-resident dependency the moved logic references stays in server.py
# and is injected here AFTER each is defined (one-way boundary: this module never
# imports server). Registries/objects are injected BY REFERENCE so server-side
# in-place mutation stays visible (_VERB_CATALOG, _A2A_PEERS, the cost ledger, the
# tracer, the kernel). The flag/scalar constants (COST_*, BACKEND) are stable.
# Placeholders keep a standalone ``import mios_http_caps`` working for the unit
# tests; the routes are runtime-only so nothing fires before configure() runs.
_VERB_CATALOG: dict = {}
_A2A_PEERS: dict = {}
_A2A_PEERS_LOCK = None
_KERNEL = None
_COST_LEDGER = None
_COST_MODEL = None
COST_ACCOUNTING_ENABLE = False
COST_BUDGET_USD = 0.0
_TRACER = None
BACKEND = ""

_verb_to_openai_tool = None
_recipe_to_openai_tool = None
_skill_to_openai_tool = None
_load_recipe_catalog = None
_skill_list = None
_skill_fetch = None
_user_rbac_filter = None
_match_user_cfg = None
_toml_section = None
_cap_skills = None
_get_client = None
kg_lookup = None
execute_skill = None
run_dci_flow = None
_offline_posture = None
# R13: the read-only prompt-registry + run-template observability routes joined this
# module's read-only admin surface. _PROMPT_REGISTRY (the live PromptRegistry instance
# built in server) + _db_read (the DB read helper) + RUN_TEMPLATE_ENABLE (the capture
# flag, SSOT-owned in mios_dag_exec) arrive by reference/value via configure().
_PROMPT_REGISTRY = None
_db_read = None
RUN_TEMPLATE_ENABLE = False


def configure(*, verb_catalog=None, a2a_peers=None, a2a_peers_lock=None,
              kernel=None, cost_ledger=None, cost_model=None,
              cost_accounting_enable=None, cost_budget_usd=None, tracer=None,
              backend=None, verb_to_openai_tool=None, recipe_to_openai_tool=None,
              skill_to_openai_tool=None, load_recipe_catalog=None, skill_list=None,
              skill_fetch=None, user_rbac_filter=None, match_user_cfg=None,
              toml_section=None, cap_skills=None, get_client=None, kg_lookup=None,
              execute_skill=None, run_dci_flow=None, offline_posture=None,
              prompt_registry=None, db_read=None, run_template_enable=None) -> None:
    """Inject server.py's runtime deps under their EXACT original names. Objects
    (catalog/peers/ledger/tracer/kernel) are passed BY REFERENCE so server-side
    mutation stays visible; the moved logic is byte-identical."""
    g = globals()
    if verb_catalog is not None:
        g["_VERB_CATALOG"] = verb_catalog
    if a2a_peers is not None:
        g["_A2A_PEERS"] = a2a_peers
    if a2a_peers_lock is not None:
        g["_A2A_PEERS_LOCK"] = a2a_peers_lock
    if kernel is not None:
        g["_KERNEL"] = kernel
    if cost_ledger is not None:
        g["_COST_LEDGER"] = cost_ledger
    if cost_model is not None:
        g["_COST_MODEL"] = cost_model
    if cost_accounting_enable is not None:
        g["COST_ACCOUNTING_ENABLE"] = cost_accounting_enable
    if cost_budget_usd is not None:
        g["COST_BUDGET_USD"] = cost_budget_usd
    if tracer is not None:
        g["_TRACER"] = tracer
    if backend is not None:
        g["BACKEND"] = backend
    if verb_to_openai_tool is not None:
        g["_verb_to_openai_tool"] = verb_to_openai_tool
    if recipe_to_openai_tool is not None:
        g["_recipe_to_openai_tool"] = recipe_to_openai_tool
    if skill_to_openai_tool is not None:
        g["_skill_to_openai_tool"] = skill_to_openai_tool
    if load_recipe_catalog is not None:
        g["_load_recipe_catalog"] = load_recipe_catalog
    if skill_list is not None:
        g["_skill_list"] = skill_list
    if skill_fetch is not None:
        g["_skill_fetch"] = skill_fetch
    if user_rbac_filter is not None:
        g["_user_rbac_filter"] = user_rbac_filter
    if match_user_cfg is not None:
        g["_match_user_cfg"] = match_user_cfg
    if toml_section is not None:
        g["_toml_section"] = toml_section
    if cap_skills is not None:
        g["_cap_skills"] = cap_skills
    if get_client is not None:
        g["_get_client"] = get_client
    if kg_lookup is not None:
        g["kg_lookup"] = kg_lookup
    if execute_skill is not None:
        g["execute_skill"] = execute_skill
    if run_dci_flow is not None:
        g["run_dci_flow"] = run_dci_flow
    if offline_posture is not None:
        g["_offline_posture"] = offline_posture
    if prompt_registry is not None:
        g["_PROMPT_REGISTRY"] = prompt_registry
    if db_read is not None:
        g["_db_read"] = db_read
    if run_template_enable is not None:
        g["RUN_TEMPLATE_ENABLE"] = run_template_enable


# ── /v1/verbs + /v1/tools projections ─────────────────────────────────────
async def list_verbs_logic(include_rare: bool = True) -> JSONResponse:
    tools = []
    for vname, vcfg in _VERB_CATALOG.items():
        if not include_rare and vcfg.get("tier") == "rare":
            continue
        props: dict = {}
        required: list[str] = []
        for argname, argcfg in (vcfg.get("params") or {}).items():
            if not isinstance(argcfg, dict):
                continue
            spec: dict = {
                "type": argcfg.get("type", "string"),
                "description": argcfg.get("desc", ""),
            }
            if argcfg.get("enum"):
                spec["enum"] = list(argcfg["enum"])
            if "default" in argcfg:
                spec["default"] = argcfg["default"]
            else:
                required.append(argname)
            props[argname] = spec
        tools.append({
            "name": vname,
            "description": vcfg.get("desc", ""),
            "inputSchema": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
            "annotations": {
                "section": vcfg.get("section", ""),
                "tier": vcfg.get("tier", "common"),
                "readOnlyHint": vcfg.get("permission") == "read",
                "permission": vcfg.get("permission", "read"),
            },
        })
    return JSONResponse({"tools": tools})


async def list_verbs_openai_tools_logic(include_rare: bool = True) -> JSONResponse:
    tools = [
        _verb_to_openai_tool(vname, vcfg)
        for vname, vcfg in _VERB_CATALOG.items()
        if include_rare or vcfg.get("tier") != "rare"
    ]
    return JSONResponse({"tools": tools, "count": len(tools)})


async def list_tools_logic(include_rare: bool = True) -> JSONResponse:
    tools = [
        _verb_to_openai_tool(vname, vcfg)
        for vname, vcfg in _VERB_CATALOG.items()
        if include_rare or vcfg.get("tier") != "rare"
    ]
    # (b) OS recipes -- the os_recipe verb's catalog, surfaced as first-class
    # tools (degrade-open: a TOML parse failure drops recipes, keeps verbs).
    recipe_n = 0
    try:
        for rname, rcfg in (_load_recipe_catalog() or {}).items():
            tools.append(_recipe_to_openai_tool(rname, rcfg))
            recipe_n += 1
    except Exception:  # noqa: BLE001 -- best-effort section; degrade open
        pass
    # (c) Promoted skills -- the executable skill library, surfaced as
    # mios_skill__* tools (degrade-open: a DB outage drops skills only).
    skill_n = 0
    try:
        for srow in (await _skill_list(status="promoted")) or []:
            tools.append(_skill_to_openai_tool(srow))
            skill_n += 1
    except Exception:  # noqa: BLE001 -- best-effort section; degrade open
        pass
    # WS-2: apply per-USER RBAC to the DISCOVERY manifest too -- previously the
    # filter ran only at fan-out dispatch (server.py:14792), so /v1/tools exposed
    # the FULL surface to a restricted user (a verb pruned from dispatch still
    # appeared discoverable). Now the manifest matches what the user can actually
    # run. No-op when no [users.*] policy matches (single-user unaffected); recipe/
    # skill tools (non-verb names) pass through unless explicitly denied.
    tools = _user_rbac_filter(tools)
    _rn = sum(1 for t in tools
              if str((t.get("function") or {}).get("name") or "").startswith("mios_recipe__"))
    _sn = sum(1 for t in tools
              if str((t.get("function") or {}).get("name") or "").startswith("mios_skill__"))
    return JSONResponse({
        "tools": tools,
        "count": len(tools),
        "counts": {
            "verbs": len(tools) - _rn - _sn,
            "recipes": _rn,
            "skills": _sn,
        },
    })


# ── MCP Resource projectors (moved here; re-imported by server.py) ────────
def _skill_to_mcp_resource(srow: dict) -> dict:
    name = str(srow.get("name") or "")
    return {
        "uri": f"mios://skill/{name}",
        "name": name,
        "description": (str(srow.get("description") or ""))[:300],
        "mimeType": "text/markdown",
        "annotations": {"miosKind": "skill", "status": srow.get("status")},
    }


def _recipe_to_mcp_resource(rname: str, rcfg: dict) -> dict:
    desc = rcfg.get("description") or rcfg.get("desc") or rcfg.get("summary") or ""
    return {
        "uri": f"mios://recipe/{rname}",
        "name": rname,
        "description": str(desc)[:300],
        "mimeType": "application/json",
        "annotations": {"miosKind": "recipe"},
    }


def _verb_to_mcp_resource(vname: str, vcfg: dict) -> dict:
    desc = vcfg.get("description") or vcfg.get("desc") or vcfg.get("summary") or ""
    return {
        "uri": f"mios://verb/{vname}",
        "name": vname,
        "description": str(desc)[:300],
        "mimeType": "application/json",
        "annotations": {"miosKind": "verb", "tier": vcfg.get("tier")},
    }


async def v1_capabilities_logic(request: Request) -> JSONResponse:
    try:
        try:
            _, _ucfg = _match_user_cfg()
        except Exception:  # noqa: BLE001
            _ucfg = {}
        ceiling = str((_ucfg or {}).get("max_permission") or "interactive")
        man = mios_capreg.build_capability_manifest(
            _VERB_CATALOG, _toml_section("recipes") or {}, ceiling=ceiling,
            skills=_cap_skills())
        return JSONResponse({"object": "mios.capability.manifest",
                             "ceiling": ceiling,
                             "summary": mios_capreg.manifest_summary(man),
                             "data": man})
    except Exception as e:  # noqa: BLE001 -- never 500 the surface
        return JSONResponse({"object": "mios.capability.manifest",
                             "error": str(e), "data": []})


async def v1_capabilities_dag_logic() -> JSONResponse:
    try:
        dag = mios_capreg.build_capability_dag(
            _VERB_CATALOG, _toml_section("recipes") or {}, _cap_skills())
        return JSONResponse({"object": "mios.capability.dag",
                             "counts": {"nodes": len(dag["nodes"]),
                                        "edges": len(dag["edges"]),
                                        "cycles": len(dag["cycles"]),
                                        "dangling": len(dag["dangling"])},
                             **dag})
    except Exception as e:  # noqa: BLE001 -- never 500 the surface
        return JSONResponse({"object": "mios.capability.dag",
                             "error": str(e), "nodes": [], "edges": []})


async def v1_peers_logic() -> JSONResponse:
    try:
        async with _A2A_PEERS_LOCK:
            peers = [{"id": pid,
                      "endpoint": str(p.get("url") or ""),
                      "heartbeat": int(p.get("heartbeat", 1) or 1)}
                     for pid, p in _A2A_PEERS.items()]
        return JSONResponse({"object": "mios.peer.digest", "peers": peers})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"object": "mios.peer.digest", "error": str(e),
                             "peers": []})


async def list_resources_logic() -> JSONResponse:
    resources: list = [
        _verb_to_mcp_resource(vname, vcfg)
        for vname, vcfg in _VERB_CATALOG.items()
    ]
    try:
        for rname, rcfg in (_load_recipe_catalog() or {}).items():
            resources.append(_recipe_to_mcp_resource(rname, rcfg))
    except Exception:  # noqa: BLE001 -- best-effort section; degrade open
        pass
    try:
        for srow in (await _skill_list(status="all", limit=1000)) or []:
            resources.append(_skill_to_mcp_resource(srow))
    except Exception:  # noqa: BLE001 -- best-effort section; degrade open
        pass
    return JSONResponse({"resources": resources, "count": len(resources)})


async def read_resource_logic(uri: str = "") -> JSONResponse:
    uri = (uri or "").strip()
    try:
        if uri.startswith("mios://skill/"):
            nm = uri[len("mios://skill/"):]
            rows = await _skill_list(status="all", limit=1000)
            row = next((s for s in (rows or [])
                        if str(s.get("name")) == nm), None)
            if row is None:
                return JSONResponse({"error": f"no such skill: {nm}"},
                                    status_code=404)
            text = str(row.get("body") or row.get("description") or "")
            mime = "text/markdown"
        elif uri.startswith("mios://recipe/"):
            nm = uri[len("mios://recipe/"):]
            rcfg = (_load_recipe_catalog() or {}).get(nm)
            if rcfg is None:
                return JSONResponse({"error": f"no such recipe: {nm}"},
                                    status_code=404)
            text = json.dumps(rcfg, ensure_ascii=False, indent=2)
            mime = "application/json"
        elif uri.startswith("mios://verb/"):
            nm = uri[len("mios://verb/"):]
            vcfg = _VERB_CATALOG.get(nm)
            if vcfg is None:
                return JSONResponse({"error": f"no such verb: {nm}"},
                                    status_code=404)
            text = json.dumps(vcfg, ensure_ascii=False, indent=2)
            mime = "application/json"
        else:
            return JSONResponse({"error": f"unknown resource uri: {uri}"},
                                status_code=404)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"contents": [
        {"uri": uri, "mimeType": mime, "text": text}]})


# ── Kernel Router shadow ──────────────────────────────────────────────────
async def v1_route_logic(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    refined = (body.get("refined") if isinstance(body, dict) and "refined" in body
               else body)
    dec = _KERNEL.router.route(refined if isinstance(refined, dict) else {})
    return JSONResponse({"object": "mios.route_decision", **dec.to_dict()})


# ── WS-RES-GOV cost ledger ────────────────────────────────────────────────
async def cost_ledger_logic() -> JSONResponse:
    return JSONResponse({
        "object": "mios.cost",
        "enabled": COST_ACCOUNTING_ENABLE,
        "budget_usd": COST_BUDGET_USD,
        "over_budget": _COST_LEDGER.over_budget(COST_BUDGET_USD),
        "model": {"gpu_watts": _COST_MODEL.gpu_watts,
                  "usd_per_kwh": _COST_MODEL.usd_per_kwh,
                  "remote_usd_per_mtok": _COST_MODEL.remote_usd_per_mtok},
        **_COST_LEDGER.snapshot(),
    })


# ── WS-A8 trace ring-buffer reads ─────────────────────────────────────────
async def trace_read_logic(trace_id: str) -> JSONResponse:
    spans = _TRACER.get_trace(str(trace_id))
    return JSONResponse({
        "object": "mios.trace",
        "trace_id": str(trace_id),
        "enabled": _TRACER.enabled,
        "span_count": len(spans),
        "spans": spans,
    })


async def trace_recent_logic() -> JSONResponse:
    return JSONResponse({
        "object": "mios.trace.list",
        **_TRACER.stats(),
        "recent": _TRACER.recent(50),
    })


# ── Offline-computation posture ───────────────────────────────────────────
async def offline_status_logic() -> JSONResponse:
    return JSONResponse({"object": "mios.offline_status", **_offline_posture(),
                         "ts": int(time.time())})


# ── WS-LIFECYCLE-VER versioned hop-prompt registry (read-only) ─────────────
async def prompt_registry_view_logic() -> JSONResponse:
    snap = _PROMPT_REGISTRY.snapshot()
    return JSONResponse({"object": "mios.prompt_registry",
                         "count": len(snap), "prompts": snap})


# ── WS-6 captured DAG run-templates (read-only) ───────────────────────────
async def run_templates_list_logic() -> JSONResponse:
    rows: list = []
    try:
        resp = await _db_read(
            "SELECT class, summary, node_count, ts FROM run_template "
            "ORDER BY ts DESC LIMIT 50;",
            pg_sql="SELECT class, summary, node_count, ts FROM run_template "
                   "ORDER BY ts DESC LIMIT 50")
        for st in (resp or []):
            if isinstance(st, dict) and isinstance(st.get("result"), list):
                rows = st["result"]
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"object": "mios.run_templates", "error": str(e),
                             "templates": []})
    return JSONResponse({"object": "mios.run_templates",
                         "enabled": RUN_TEMPLATE_ENABLE,
                         "count": len(rows), "templates": rows})


# ── /v1/models (passthrough) ───────────────────────────────────────────────
async def list_models_logic(request: Request) -> JSONResponse:
    # Advertise EXACTLY ONE model on the pipeline's public surface: "MiOS AI".
    # ANY OpenAI-compatible client (OWUI, Firefox Smart Window, the desktop, the
    # CLI) lists + selects it WITHOUT a backend key -- /v1/chat/completions runs
    # the chain locally and needs no auth. The id is the SSOT [ai].agent_model
    # ("MiOS AI"), NOT a hardcode. Operator directive: "JUST MiOS AI for
    # everything advertised in the pipeline" -- so we DO NOT augment with the raw
    # backend lane list even when the caller sends Authorization; the internal
    # lane/model ids (granite4.1:8b, mios-heavy, mios-opencode, ...) are plumbing,
    # never advertised. A client that genuinely needs a raw lane addresses that
    # lane's own endpoint directly.
    created = int(time.time())
    _agent_id = str((_toml_section("ai") or {}).get("agent_model") or "MiOS AI")
    # Advertise a large context so strict clients (e.g. the Hermes desktop, which
    # enforces a 64K floor) accept the model. The chain manages real context budget
    # internally per node; this is the logical window the front door exposes.
    _ctx = int(os.environ.get("MIOS_AGENT_PIPE_CTX", "65536"))
    models: list = [{
        "id": _agent_id, "object": "model",
        "created": created, "owned_by": "mios",
        "max_model_len": _ctx, "context_length": _ctx,
        "max_context_length": _ctx, "context_window": _ctx,
    }]
    return JSONResponse(content={"object": "list", "data": models})


# ── /v1/embeddings (passthrough) ───────────────────────────────────────────
async def embeddings_logic(request: Request) -> JSONResponse:
    body = await request.body()
    client = await _get_client()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("authorization", "content-type")}
    try:
        r = await client.post(
            f"{BACKEND}/embeddings", content=body, headers=headers,
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except httpx.HTTPError as e:
        log.warning("embeddings proxy failed: %s", e)
        return JSONResponse(
            content={"error": {"message": str(e), "type": "backend_error"}},
            status_code=502,
        )


# ── /kg/lookup (Personal Knowledge Graph) ─────────────────────────────────
async def kg_lookup_endpoint_logic(phrase: str = "") -> JSONResponse:
    if not phrase:
        return JSONResponse(
            content={"error": "phrase query param required"},
            status_code=400,
        )
    result = await kg_lookup(phrase)
    if result is None:
        return JSONResponse(
            content={"match": None, "phrase": phrase},
            status_code=404,
        )
    return JSONResponse(content={"match": result, "phrase": phrase})


# ── /skills/* (cross-agent skill catalog) ─────────────────────────────────
async def skills_list_logic(status: str = "promoted",
                            source: str = "",
                            limit: int = 200) -> JSONResponse:
    rows = await _skill_list(
        status=status or "all",
        source=source or None,
        limit=max(1, min(int(limit or 200), 1000)),
    )
    return JSONResponse(content={"skills": rows, "count": len(rows)})


async def skills_show_logic(name: str = "") -> JSONResponse:
    if not name:
        return JSONResponse(
            content={"error": "name query param required"},
            status_code=400)
    row = await _skill_fetch(name)
    if not row:
        return JSONResponse(content={"skill": None, "name": name},
                            status_code=404)
    return JSONResponse(content={"skill": row})


async def skills_run_logic(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"}, status_code=400)
    name = str(body.get("name", "")).strip()
    if not name:
        return JSONResponse(
            content={"error": "name required"}, status_code=400)
    params = body.get("params") or {}
    if not isinstance(params, dict):
        return JSONResponse(
            content={"error": "params must be an object"},
            status_code=400)
    session_id = body.get("session_id")
    result = await execute_skill(
        name, params, session_id=session_id)
    status_code = 200 if result.get("success") else 422
    return JSONResponse(content=result, status_code=status_code)


async def skills_openai_tools_logic() -> JSONResponse:
    rows = await _skill_list(status="promoted")
    tools = [_skill_to_openai_tool(r) for r in rows]
    return JSONResponse(content={"tools": tools, "count": len(tools)})


# ── /dci/* (deliberation surface) ─────────────────────────────────────────
async def dci_deliberate_logic(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"},
            status_code=400,
        )
    user_text = str(body.get("user_text", "")).strip()
    envelope = body.get("envelope") or {}
    if not user_text:
        return JSONResponse(
            content={"error": "user_text required"}, status_code=400,
        )
    if not isinstance(envelope, dict):
        return JSONResponse(
            content={"error": "envelope must be an object"},
            status_code=400,
        )
    r_max = body.get("r_max")
    if r_max is not None:
        try:
            r_max = max(1, min(int(r_max), 5))
        except (TypeError, ValueError):
            r_max = None
    result = await run_dci_flow(
        user_text, envelope,
        session_id=body.get("session_id"),
        r_max=r_max,
    )
    return JSONResponse(content=result)


async def dci_schema_logic() -> JSONResponse:
    return JSONResponse(content={
        "acts": _DCI_ACTS,
        "act_names": _DCI_ACT_NAMES,
        "response_schema": _DCI_ACT_SCHEMA,
        "enabled": DCI_ENABLED,
    })


# -- @app -> APIRouter migration (refactor R13 batch 2: federation/standards) ----
# The gossip peer-digest (/v1/peers) + the MCP-Resources discovery surface
# (/v1/resources, /v1/resources/read) moved off server.py's @app onto this
# co-located http_caps_router (same routes->APIRouter pattern the /a2a wave
# established). server.py imports http_caps_router + the three handler NAMES and
# mounts the router via app.include_router(http_caps_router); the handler names are
# re-imported there so server's importable `provided` surface is unchanged and the
# served path/method set is identical (the live-app route gate proves it). Each body
# now calls the module-resident *_logic DIRECTLY (same module -- no sys.modules hop).
# One-way boundary: this module never imports server (the verb catalog + peer
# registry the logic reads arrive via configure()). APIRouter()/method decorators
# are structural, not config.
http_caps_router = APIRouter()


@http_caps_router.get("/v1/peers")
async def v1_peers() -> JSONResponse:
    """WS-A18 gossip anti-entropy digest: this node's known A2A peers
    {id, endpoint, heartbeat}. Other nodes PULL this each gossip round and merge
    it (trust-gated) into their own peer set, so the federation discovers peers
    epidemically without a central registry. Additive + read-only. Calls
    v1_peers_logic (same module)."""
    return await v1_peers_logic()


@http_caps_router.get("/v1/resources")
async def list_resources() -> JSONResponse:
    """The COMPLETE read-only MiOS capability surface as MCP Resources: every
    verb (the script surface), every recipe, and EVERY skill (promoted AND
    not). Browsable discovery that complements the curated callable /v1/tools
    feed -- so the agent can reach the whole catalog without the flat tool list
    growing past the ~30-50 where selection accuracy drops. Degrade-open: a
    failing section drops only itself. Calls list_resources_logic (same module)."""
    return await list_resources_logic()


@http_caps_router.get("/v1/resources/read")
async def read_resource(uri: str = "") -> JSONResponse:
    """Fetch ONE mios:// resource (skill body / recipe def / verb doc) in MCP
    resources/read shape: {contents:[{uri,mimeType,text}]}. Unknown scheme ->
    404. Degrade-open on backend error. Calls read_resource_logic (same module)."""
    return await read_resource_logic(uri)


# -- @app -> APIRouter migration (refactor R13 batch 3: capability/observability) --
# The RBAC-filtered capability manifest + DAG, the kernel Router shadow, the cost
# ledger, the trace ring-buffer reads, the offline posture, the versioned hop-prompt
# registry and the captured DAG run-templates -- all read-only capability/admin
# surfaces this module already owns the LOGIC for -- moved off server.py's @app onto
# this co-located http_caps_router (the same routes->APIRouter pattern the /a2a wave
# established). server.py imports the handler NAMES (re-imported there so its
# importable `provided` surface is unchanged) + already mounts the router via
# app.include_router(http_caps_router); the served path/method set is identical (the
# live-app route gate proves it). Each body calls the module-resident *_logic
# DIRECTLY (same module -- no sys.modules hop).
@http_caps_router.get("/v1/capabilities")
async def v1_capabilities(request: Request) -> JSONResponse:
    """WS-2 unified, RBAC-filtered capability manifest: the single list of
    capabilities (verbs + recipes) the CALLER may use, filtered by their
    permission ceiling (matched [users.*].max_permission via the same lattice the
    PDP uses; default 'interactive' = the full known-tier surface when no
    principal/ceiling is forwarded). One projection over the [verbs.*]+[recipes.*]
    SSOT (mios_capreg) -- the live counterpart of the committed
    ai/v1/capabilities.generated.json. Degrade-open."""
    return await v1_capabilities_logic(request)


@http_caps_router.get("/v1/capabilities/dag")
async def v1_capabilities_dag() -> JSONResponse:
    """WS-2 structured capability DAG: nodes (verbs|recipes|skills) + edges (each
    skill -> the verb/skill its steps invoke), with detected skill->skill `cycles`
    and `dangling` step targets (a step naming an unknown verb/skill). The
    structural counterpart of the flat /v1/capabilities manifest -- lets a caller
    (or an A2A peer) see WHICH primitives a skill composes + validate the graph is
    acyclic + fully-grounded. Read-only, degrade-open, NOT RBAC-filtered (it is the
    full authored graph; /v1/capabilities is the per-caller filtered view)."""
    return await v1_capabilities_dag_logic()


@http_caps_router.post("/v1/route")
async def v1_route(request: Request) -> JSONResponse:
    """WS-A11/WS-3 Router introspection: classify a refined plan WITHOUT executing
    it. POST a bare refined dict or {"refined": {...}} -> the typed RouteDecision
    {mode, intent, tool, fanout, reason}. Lets an operator confirm the decomposed
    Router matches the inline chat_completions cascade before the Stage-2b
    execution swap. Pure + read-only."""
    return await v1_route_logic(request)


@http_caps_router.get("/v1/cost")
async def cost_ledger() -> JSONResponse:
    """WS-RES-GOV cost/energy accounting (CLASSic Cost axis): the running ledger
    of dispatch energy (Wh) + $ + tokens, broken down per lane, since process
    start. Observe-only; populated when [cost].enable is on. The power envelope is
    the real constraint on a local-GPU OS, so this surfaces it as a first-class
    signal (complements the token-rate budget tripwire)."""
    return await cost_ledger_logic()


@http_caps_router.get("/v1/trace/{trace_id}")
async def trace_read(trace_id: str) -> JSONResponse:
    """WS-A8: return the recorded spans for one trace (zero DB hit -- served
    from the in-memory ring buffer). 404-shaped empty object when unknown or
    already evicted past the buffer cap."""
    return await trace_read_logic(trace_id)


@http_caps_router.get("/v1/trace")
async def trace_recent() -> JSONResponse:
    """WS-A8: list the most-recent traces still in the buffer (newest first)."""
    return await trace_recent_logic()


@http_caps_router.get("/v1/offline-status")
async def offline_status() -> JSONResponse:
    """Live offline-computation posture: every inference/embedding/agent
    endpoint classified local-vs-external. `offline: true` proves no MiOS
    compute path egresses to a cloud host ('maintain offline computation for all
    MiOS systems'). Calls offline_status_logic (same module)."""
    return await offline_status_logic()


@http_caps_router.get("/v1/prompts")
async def prompt_registry_view() -> JSONResponse:
    """WS-LIFECYCLE-VER versioned hop-prompt registry: each live system prompt's
    version + content-hash + length + history depth (content-FREE -- never leaks
    the prompt text). The substrate for self-improve rollback + prompt-drift
    detection. Empty until the startup registration runs. Calls
    prompt_registry_view_logic (same module)."""
    return await prompt_registry_view_logic()


@http_caps_router.get("/v1/run-templates")
async def run_templates_list() -> JSONResponse:
    """WS-6 determinism foundation: recent captured DAG run-templates (the
    replayable plan shapes). Replay-reuse is a follow-up; this is capture +
    observability. Calls run_templates_list_logic (same module)."""
    return await run_templates_list_logic()


# -- @app -> APIRouter migration (refactor R13 batch 4: verb/tool catalog +
# personal knowledge graph + cross-agent skills + DCI surface) --------------
# The advertised-capability discovery routes whose *_logic bodies already home
# here -- the verb catalog (MCP `inputSchema` projection + OpenAI tools twin),
# the unified verb+recipe+skill tool feed, the personal-knowledge-graph phrase
# lookup, the cross-agent skill catalog (list/show/run/openai-tools), and the
# DCI deliberation+schema surface -- moved off server.py's @app onto this SAME
# co-located http_caps_router (the routes->APIRouter pattern the /a2a wave
# established). server.py re-imports each handler NAME so its importable
# `provided` surface is unchanged and the served path/method set is
# byte-identical (the live-app route gate proves it). Each body now calls the
# module-resident *_logic DIRECTLY (same module -- no sys.modules hop); every
# dep the logic reads is already injected by the configure() pass above.
@http_caps_router.get("/v1/verbs")
async def list_verbs(include_rare: bool = True) -> JSONResponse:
    """Render [verbs.*] as JSON-Schema tool specs. Same SSOT that
    drives the planner catalog. Consumed by mios-mcp-server (for
    MCP `tools/list`) and any external tooling that wants the
    canonical verb shape."""
    return await list_verbs_logic(include_rare)


@http_caps_router.get("/v1/verbs/openai-tools")
async def list_verbs_openai_tools(include_rare: bool = True) -> JSONResponse:
    """The MiOS verb catalog projected into the OpenAI `tools=` array shape.

 include_rare defaults TRUE ("ALL global agents and
    sub-agents able to use ALL the tools"). Broker dispatch access was already
    global; this makes the PRESENTED surface complete too -- no verb (incl
    crawl, and other former tier=rare entries) is hidden behind tool_search.
    Pass include_rare=false for the trimmed set if a context-budget-limited
    client needs it.

    The OpenAI-shape twin of /v1/verbs (which serves the MCP `inputSchema`
    shape for mios-mcp-server). Hermes already carries the full MiOS verb +
    skill surface alongside its own built-in tools, so this is NOT how
    Hermes gets its tools. It exists so any STRICT OpenAI tool-loop client
    that lacks the MiOS plugin -- an external /v1 caller, OpenCode in a
    tools= mode, an A2A/ACP peer -- can be handed the verb surface in the
    standard shape and call it via POST /v1/dispatch {tool,args} (same
    launcher-broker path the MCP server uses). One SSOT (_VERB_CATALOG),
    three projections: MCP (/v1/verbs), OpenAI tools (here), A2A skills
    (the agent card). Discover here, execute at /v1/dispatch."""
    return await list_verbs_openai_tools_logic(include_rare)


@http_caps_router.get("/v1/tools")
async def list_tools(include_rare: bool = True) -> JSONResponse:
    """The COMPLETE MiOS capability surface as MCP tool specs: every verb
    PLUS every OS recipe PLUS every promoted skill, in one feed.

    This is the unified discovery endpoint mios-mcp-server's `tools/list`
    consumes so an MCP client sees the WHOLE surface, not just the verb
    catalog. /v1/verbs is left UNCHANGED (verbs only) for existing
    consumers; this is the superset.

    Three projections, one MCP `inputSchema`/function shape:
      (a) verbs   -> _verb_to_openai_tool   (name == bare verb)
      (b) recipes -> _recipe_to_openai_tool (name == mios_recipe__<name>)
      (c) skills  -> _skill_to_openai_tool  (name == mios_skill__<name>)

    The relay routes a returned tool_call by name prefix: a bare name ->
    POST /v1/dispatch {tool,args}; mios_recipe__* -> os_recipe; mios_skill__*
    -> POST /skills/run. Discover here, execute there -- one contract.

    Degrade-open: a recipe-load or skill-DB failure drops only THAT section,
    never the others, so an offline datastore still yields the full verb +
    recipe surface (operator: tools must stay available even when a subsystem
    is down)."""
    return await list_tools_logic(include_rare)


@http_caps_router.get("/kg/lookup")
async def kg_lookup_endpoint(phrase: str = "") -> JSONResponse:
    return await kg_lookup_endpoint_logic(phrase)


@http_caps_router.get("/skills/list")
async def skills_list(status: str = "promoted",
                      source: str = "",
                      limit: int = 200) -> JSONResponse:
    return await skills_list_logic(status, source, limit)


@http_caps_router.get("/skills/show")
async def skills_show(name: str = "") -> JSONResponse:
    return await skills_show_logic(name)


@http_caps_router.post("/skills/run")
async def skills_run(request: Request) -> JSONResponse:
    return await skills_run_logic(request)


@http_caps_router.get("/skills/openai-tools")
async def skills_openai_tools() -> JSONResponse:
    """Dump the OpenAI tool-schema array for every promoted skill.
    Hermes + OpenCode fetch this and append it to their static tool
    surface so promoted skills become first-class callable tools
    on every external gateway -- no client-side edits per skill."""
    return await skills_openai_tools_logic()


@http_caps_router.post("/dci/deliberate")
async def dci_deliberate(request: Request) -> JSONResponse:
    return await dci_deliberate_logic(request)


@http_caps_router.get("/dci/schema")
async def dci_schema() -> JSONResponse:
    return await dci_schema_logic()


# -- @app -> APIRouter migration (refactor R13): the /v1/models + /v1/embeddings
# passthrough routes whose *_logic bodies already home here moved off server.py's @app
# onto this SAME co-located http_caps_router. server.py re-imports both handler NAMES
# so its importable `provided` surface is unchanged and the served path/method set is
# byte-identical (the live-app route gate proves it). Each body calls the
# module-resident *_logic DIRECTLY (same module -- no sys.modules hop).
# ── /v1/models (passthrough) ───────────────────────────────────────
@http_caps_router.get("/v1/models")
async def list_models(request: Request) -> JSONResponse:
    # Advertise EXACTLY ONE model on the pipeline's public surface: "MiOS AI".
    # ANY OpenAI-compatible client (OWUI, Firefox Smart Window, the desktop, the
    # CLI) lists + selects it WITHOUT a backend key -- /v1/chat/completions runs
    # the chain locally and needs no auth. The id is the SSOT [ai].agent_model
    # ("MiOS AI"), NOT a hardcode. Operator directive: "JUST MiOS AI for
    # everything advertised in the pipeline" -- so we DO NOT augment with the raw
    # backend lane list even when the caller sends Authorization; the internal
    # lane/model ids are plumbing, never advertised. A client that genuinely needs
    # a raw lane addresses that lane's own endpoint directly.
    return await list_models_logic(request)


# ── /v1/embeddings (passthrough) ───────────────────────────────────
@http_caps_router.post("/v1/embeddings")
async def embeddings(request: Request) -> JSONResponse:
    return await embeddings_logic(request)

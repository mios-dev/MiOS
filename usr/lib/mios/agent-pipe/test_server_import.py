#!/usr/bin/env python3
# AI-hint: Near-runtime import gate for the agent-pipe strangler-fig refactor (WS R0+). Stubs the 3rd-party deps not guaranteed on a bare checkout (httpx/websockets/uvicorn + a minimal fastapi) so that `import server` actually EXECUTES every module-level statement: all config, all defs, EVERY re-import of an extracted symbol, and EVERY stacked `sys.modules["mios_*"].configure(...)` dependency-injection call. A misordered configure() (an injected symbol referenced before it is defined) raises a NameError HERE — the exact runtime regression class that py_compile (syntax-only) and mios_surface (ast, no execution) cannot catch. Then asserts each extracted symbol resolves to its sibling module (server is a thin re-export shim for them). Importing has no side effects: uvicorn.run is __main__-guarded and the background daemons start in the FastAPI lifespan, not at import. Pure stdlib + unittest.mock. Run after every extraction wave.
# AI-related: ./server.py, ./mios_surface.py, ./mios_config.py, ./mios_grounding.py, ./mios_verity.py, ./mios_skills.py, ./mios_fanout.py, ./mios_dci.py
# AI-functions: _install_stubs, _resolve_toml, check, main
"""Stub-and-import gate: prove server.py imports cleanly with all DI wired (refactor R0+)."""

import os
import sys
import types
from unittest import mock

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _resolve_toml():
    """Point MIOS_TOML at the repo's vendor mios.toml if present (repo root = 4
    levels up from this file: usr/lib/mios/agent-pipe/), so the import exercises
    the REAL config parse on any host. Harmless if absent (readers degrade)."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    toml = os.path.join(repo, "usr", "share", "mios", "mios.toml")
    if "MIOS_TOML" not in os.environ and os.path.isfile(toml):
        os.environ["MIOS_TOML"] = toml


def _install_stubs():
    """Insert minimal stand-ins for the heavy 3rd-party deps so server.py imports
    on a bare checkout. MagicMock covers httpx/websockets/uvicorn; fastapi needs a
    tiny real-ish App whose route/middleware decorators return the wrapped fn."""
    for name in ("httpx", "websockets", "uvicorn"):
        sys.modules.setdefault(name, mock.MagicMock(name=name))

    fastapi = types.ModuleType("fastapi")

    class _App:
        def __getattr__(self, _attr):
            def _decorator_factory(*_a, **_k):
                def _wrap(fn=None):
                    return fn if fn is not None else (lambda f: f)
                return _wrap
            return _decorator_factory

    fastapi.FastAPI = lambda *a, **k: _App()
    # APIRouter behaves like the app here: a decorator-factory object whose
    # .get/.post/... return the wrapped handler unchanged. R13 moved the /a2a routes
    # onto an APIRouter in mios_a2a, mounted by server via app.include_router.
    fastapi.APIRouter = lambda *a, **k: _App()
    fastapi.Request = object
    fastapi.WebSocket = object
    responses = types.ModuleType("fastapi.responses")
    for _c in ("HTMLResponse", "JSONResponse", "RedirectResponse",
               "Response", "StreamingResponse"):
        setattr(responses, _c, type(_c, (), {"__init__": lambda self, *a, **k: None}))
    fastapi.responses = responses
    sys.modules.setdefault("fastapi", fastapi)
    sys.modules.setdefault("fastapi.responses", responses)


# Every symbol the refactor has extracted -> the sibling module it now lives in.
# server.py must still PROVIDE each (as a re-import) and it must resolve to the
# sibling, proving the extraction preserved the importable surface. Grows per wave.
_EXTRACTED = {
    "mios_pipe.kernel.config": ["_toml_section", "_cfg_num", "PORT", "_STACK_MODEL"],
    "mios_pipe.routing.provider_translate": ["_scrub_schema", "_oai_msgs_to_anthropic"],
    "mios_pipe.routing.sse": ["_sse_chunk", "_sse_status", "_stream_answer", "_iter_answer_chunks"],
    "mios_pipe.routing.dci": ["run_dci_flow", "critic_then_maybe_flow"],
    "mios_endpoints": ["_endpoint_is_ollama", "_endpoint_is_llamacpp"],
    "mios_pipe.context.grounding": ["_env_grounding", "_env_block", "_host_timezone", "_current_year"],
    "mios_pipe.lifecycle.verity": ["polish_response", "_strip_ungrounded_figures", "_clarify_question"],
    # _PARAM_TOKEN_RE is re-imported for surface parity but omitted here: a compiled
    # re.Pattern reports __module__ == 're', which the origin check can't attribute.
    "mios_skills": ["execute_skill", "_make_schema_strict", "_skill_render_args",
                    "_skill_invocation_open", "_skill_invocation_close",
                    "_skill_attribute_tool_call", "_SKILL_INV_META",
                    "_slug_for_skill", "_render_skill_md", "_write_skill_md_fire"],
    "mios_pipe.routing.fanout": ["_pick_fanout_agents"],
    "mios_pipe.routing.routing": ["_load_routing_domains", "_load_routing_phrases",
                     "_load_launch_fillers", "_deterministic_action_route"],
    "mios_pipe.routing.agentreg": ["_load_agent_registry", "_load_node_pool", "_build_agent_engines",
                      "_agent_lane", "_render_agent_catalog", "_role_system",
                      "_dedup_pool_by_target"],
    "mios_pipe.memory.knowledge": ["_store_knowledge", "_recall_knowledge", "_recency_mult",
                       "_rls_owner", "_recall_agent_memory", "kg_lookup"],
    "mios_pipe.routing.refine": ["refine_intent", "_salvage_refine_dispatch", "_REFINE_SYSTEM",
                    "_critic_refine_agent"],
    "mios_pipe.routing.planner": ["decompose_intent", "_topological_order", "_dag_levels", "_PLANNER_SYSTEM"],
    "mios_pipe.routing.toolexec": ["_exec_tool_calls", "_rescue_tool_calls", "_cap_verb_result",
                      "_format_tool_error", "_record_mcp_tool_call"],
    "mios_pipe.routing.agent_call": ["_call_agent_complete", "_call_agent_complete_inner",
                        "_call_agent_stream_inner",
                        # KV-paging/fork + RR-preemptible decode cluster moved home
                        "_kv_base", "_kv_filename", "_kv_lock", "_kv_slot_action",
                        "_kv_paging", "_kv_fork", "_rr_eligible", "_rr_slice",
                        "_rr_run",
                        # per-dispatch lane-governance pair moved home (sole caller)
                        "_trip_breaker", "_num_predict_cap_for"],
    "mios_pipe.routing.secondary_loop": ["_v1_secondary_tool_loop", "_ollama_secondary_tool_loop",
                            "_daemon_diagnose", "_TOOL_NUDGE", "_REPLAN_NUDGE",
                            "_tool_call_sig", "_looks_like_disclaimer",
                            "_tmsgs_indicate_failure", "_DISCLAIM_MARKERS"],
    "mios_pipe.routing.web_research": ["_web_research_enrich", "_is_port_open",
                          "_url_has_path", "_clean_web_text",
                          "_anchor_tokens", "_shares_anchor",
                          "_src_turn_key", "_src_turn_init", "_src_record",
                          "_src_collected", "_sources_markdown", "_sources_metadata",
                          "_sources_annotations", "_filter_relevant_sources",
                          "_src_record_from_text", "_harvest_sub_sources"],
    # _SRC_LINE_RE / _SRC_URL_RE plus the relocated web-text/anchor patterns
    # (_MD_IMG_RE / _EMPTY_LINK_RE / _NAV_BULLET_RE / _INLINE_LINK_RE / _DATA_URI_RE /
    # _EMPTY_BULLET_RE / _MULTI_BLANK_RE / _ANCHOR_TOKEN_RE) and the _ANCHOR_STOPWORDS
    # frozenset are re-imported for surface parity but omitted here: a compiled
    # re.Pattern reports __module__ == 're', which the origin check can't attribute.
    "mios_pipe.access.policy": ["_perm_rank", "_effective_perm", "_agent_rbac_filter",
                    "_dispatch_pdp_reason"],
    "mios_pipe.access.firewall": ["_is_external_url", "_classify_verb_taint",
                      "_session_is_tainted"],
    "mios_pipe.access.hitlflow": ["_action_hash", "_pending_hash", "_hitl_gate",
                      "_classify_approval_reply", "hitl_approve_logic"],
    "mios_dispatch": ["dispatch_mios_verb", "_build_dispatch_cmd",
                      "_template_to_cmd", "_emit_dispatch_dedup_event",
                      "_arg_with_synonyms", "_validate_enum_args",
                      "_dispatch_sandbox_profile", "_sandbox_wrap_cmd"],
    "mios_pipe.routing.dag_exec": ["execute_dag", "_execute_dag_node",
                      "_execute_dag_bounded", "_execute_dag_emitting"],
    "mios_pipe.routing.swarm": ["_agent_dag_from_tasks", "_respond_agent_dag",
                   "_plan_swarm", "_expand_facets"],
    "mios_pipe.routing.native_loop": ["_respond_native_loop_direct", "_respond_local_state",
                         "_format_local_state", "_formulate_web_query",
                         "_formulate_compute_snippet"],
    "mios_pipe.routing.oscontrol": ["_respond_os_control", "_verify_os_action", "_window_diff",
                       "_render_os_control_verbs"],
    "mios_pipe.routing.vision": ["_vision_complete", "_has_client_tools", "_client_tools_complete"],
    "mios_pipe.memory.worker_tools": [],  # populated below if the module exposes stable names
    "mios_pipe.routing.toolsearch": ["_tool_embedding", "_ensure_verb_embeddings",
                        "_refresh_app_inventory", "_cosine", "_verb_embed_text",
                        "_verb_embed_fingerprint"],
    "mios_pipe.kernel.daemons": ["_gossip_loop", "_membership_watch_loop", "_selfimprove_report",
                     "_selfimprove_loop", "_kv_gc_sweep_once", "_kv_gc_loop",
                     # T-062/T-064 ACT half: the queued-proposals route handler moved
                     # onto the SAME daemons_router + re-imported by server (parity).
                     "selfimprove_proposals_ep"],
    "mios_pipe.routing.portal": ["_portal_authed", "_portal_token_ok", "_discover_portal_services",
                    "portal_stats_logic", "portal_service_detail_logic",
                    "portal_swarm_logic", "portal_term_ws_logic",
                    "portal_login_page_logic", "portal_login_logic",
                    "portal_page_logic"],
    "mios_pipe.federation.a2a": ["_build_agent_card", "_a2a_jsonrpc_dispatch", "_a2a_verify_principal",
                 "a2a_jsonrpc_logic", "a2a_skills_list_logic", "a2a_dispatch_logic",
                 "passport_verify_logic", "passport_public_key_logic",
                 # R13: the five /a2a route handlers moved here (off server.py's @app
                 # onto a2a_router) and are re-imported by server -- assert their home.
                 "a2a_skill_directory", "a2a_context_get", "a2a_jsonrpc",
                 "a2a_jsonrpc_alias", "a2a_peers_reload",
                 # FED-G8: the caller-key revoke route handler lives on the SAME
                 # a2a_router and is re-imported by server -- assert its home.
                 "caller_key_revoke",
                 # R13 batch 2: the discovery/identity route handlers moved here onto
                 # the SAME a2a_router and are re-imported by server -- assert home.
                 "a2a_agent_card", "a2a_agent_card_legacy", "agent_passport",
                 "agntcy_manifest_wellknown", "a2a_peers_list", "a2a_skills_list",
                 "a2a_dispatch", "passport_verify", "passport_public_key"],
    "mios_pipe.federation.a2a_client": ["_a2a_load_peers", "_a2a_send_message_to_peer",
                        "_a2a_extract_text", "_a2a_self_peer_url",
                        "_a2a_fetch_card", "_a2a_tailnet_candidates"],
    "mios_pipe.identity.principal": ["_passport_canonical_json", "_passport_op_hash",
                           "_passport_load_priv", "_passport_kid",
                           "_passport_load_public", "_passport_sign",
                           "_passport_verify", "_passport_pub_cache",
                           "_passport_load_attempted"],
    "mios_pipe.federation.mcp": ["_mcp_call_tool", "_mcp_render_headers", "_McpStdioClient",
                 # R13 batch 2: the three /v1/mcp/* route handlers moved here (off
                 # @app onto mcp_router) and are re-imported by server -- assert home.
                 "mcp_clients", "mcp_tools_list", "mcp_dispatch"],
    "mios_pipe.federation.http_caps": ["_skill_to_mcp_resource", "_recipe_to_mcp_resource",
                       "_verb_to_mcp_resource",
                       # R13 batch 2: the /v1/peers + /v1/resources[/read] route
                       # handlers moved here (off @app onto http_caps_router) and are
                       # re-imported by server -- assert their home.
                       "v1_peers", "list_resources", "read_resource"],
    # The W0-T3 aggregate-budget admission cluster moved here (sole consumer is
    # chat_completions_logic). _BUDGET_LOCK is re-imported for surface parity but
    # omitted: an asyncio.Lock instance reports __module__ == 'asyncio.locks',
    # which the origin check can't attribute (same class as the re.Pattern cases).
    "mios_pipe.routing.chat": ["chat_completions_logic", "responses_api_logic",
                  "_budget_num", "_budget_bucket", "_budget_window_total",
                  "_budget_debit", "_budget_prune_inflight", "_budget_admit",
                  "_budget_release_inflight",
                  "_BUDGET_TOML", "_BUDGET_LEDGER", "_BUDGET_LEDGER_MAX",
                  "_BUDGET_AUTO_INFLIGHT", "BUDGET_CONV_TOKEN_CEIL",
                  "BUDGET_AUTO_TOKEN_CEIL", "BUDGET_AUTO_MAX_INFLIGHT",
                  "BUDGET_WINDOW_S", "BUDGET_ENABLE", "BUDGET_PER_TURN_ESTIMATE",
                  "BUDGET_INFLIGHT_TTL_S"],
    "mios_pipe.routing.cua": ["v1_computer_use_logic", "_cua_extract_png", "_cua_screenshot_uri",
                 "_cua_vlm_json", "_cua_loop"],
    "mios_pipe.kernel.clusterhealth": ["cluster_health_logic", "scheduler_state_logic",
                           "health_logic", "_probe_one_endpoint",
                           "_lane_sched_stats", "_kernel_managers_detail"],
    "mios_pipe.routing.verbcatalog": ["_load_verb_catalog", "_resolve_verb_key",
                         "_verb_to_openai_tool"],
    "mios_pipe.routing.turn": ["_extract_last_user_text", "_pick_agent", "_live_agent_names"],
    "mios_pipe.routing.lanes_resolver": ["_pick_tool_backend", "_lane_resolver", "_heavy_lane_up"],
    "mios_pipe.scheduler.sched": ["PriorityGate", "_lane_tool_cap", "_agent_offload_engine",
                   "_resolve_autonomous_priority", "_sched_priority", "_lane_sem_key"],
    "mios_pipe.context.promptfmt": ["_council_role_lens", "_format_satisfaction_block", "_format_tool_history",
                       "_build_agent_hint", "_multi_task_preamble"],
    "mios_pipe.context.tokenize": ["_usage_estimate"],
    "mios_pipe.routing.classify": ["classify_intent", "_route_domain"],
    "mios_pipe.routing.reflect": ["_inline_satisfaction_check", "reflect_on_step_failure",
                     "_recent_satisfaction_verdicts", "_recent_tool_history",
                     "_judge_answer_satisfied"],
}


def main():
    _resolve_toml()
    _install_stubs()
    try:
        import server  # noqa: E402 -- executes ALL module-level code incl. configure() DI
    except Exception as e:  # noqa: BLE001
        import traceback
        check("import server (no NameError from DI ordering)", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()
        print(f"\n{_fails} FAILED")
        return 1
    check("import server (no NameError from DI ordering)", True)
    for module, names in _EXTRACTED.items():
        for n in names:
            obj = getattr(server, n, None)
            origin = getattr(obj, "__module__", None)
            # constants have no __module__; presence alone proves the re-import.
            ok = obj is not None and (origin in (module, None))
            check(f"{n} provided by server (-> {module})", ok,
                  "" if ok else f"missing or wrong origin: {origin!r}")

    # T-053 FED-G9: loopback-default bind derivation. Pure helper (no socket), so the
    # posture is asserted here in the import gate: loopback unless the inbound auth gate
    # is on; an explicit override wins. Both branches + the override are exercised in
    # one process (the env-read live value is only one branch).
    bh = getattr(server, "_bind_host", None)
    check("_bind_host present + callable", callable(bh))
    if callable(bh):
        check("_bind_host auth-off -> loopback", bh(False) == "127.0.0.1", bh(False))
        check("_bind_host auth-on -> all-interfaces", bh(True) == "0.0.0.0", bh(True))
        check("_bind_host explicit override wins",
              bh(False, "10.1.2.3") == "10.1.2.3", bh(False, "10.1.2.3"))

    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

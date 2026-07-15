#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for T-030 (Dual-Ledger + Typed-Output Synthesis). Pure stdlib + asyncio, no server.py/DB/network. Verifies fact_ledger & progress_ledger table insertion triggers, both-intent DAG dependency wiring, parse_research_claims extractor, fact injection into action prompts, synthesis reducer, and stall re-plan triggers.
# AI-related: ./mios_pipe/routing/dag_exec.py, ./mios_pipe/routing/swarm.py
# AI-functions: check, t_both_intent_deps, t_parse_research_claims, t_execute_dag_node_ledger_writes, t_synthesis_reducer, t_replan_stall_trigger, main
"""Unit tests for T-030 Dual-Ledger + Typed-Output Synthesis."""

import asyncio
import sys
import logging
import contextvars

logging.basicConfig(level=logging.INFO)

# Import targets
import mios_pipe.routing.dag_exec as de
import mios_pipe.routing.swarm as swarm

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# Global configuration helpers for tests
def setup_test_stubs():
    rdv = contextvars.ContextVar("routed_domain", default=None)
    # Configure swarm
    swarm.configure(
        swarm_max_width=6, swarm_max_cpu_nodes=2, swarm_deepen_enabled=False,
        slow_lane_block_chars=1500, dag_replan_max=1,
        dag_empty_native_fallback=True, slow_lanes=set(),
        agent_registry={"hermes-worker": {"model": "hermes-3"}, "gpu-node": {"model": "gpu-model"}},
        verb_catalog={}, routed_domain_var=rdv,
        pick_agent=lambda r: (r if r else "hermes-worker", {}),
        dedup_pool_by_target=lambda p: p,
        is_slow_lane_ep=lambda ep: False,
        agent_lane=lambda c: "light",
        live_agent_names=lambda: {"hermes-worker", "gpu-node"},
        read_tool_enrich=lambda *a, **k: "",
        respond_native_loop_direct=lambda *a, **k: "Direct answer",
        strip_think_tags=lambda t: t,
        filter_relevant_sources=lambda refs, *t: [],
        sources_markdown=lambda refs: "",
        sources_annotations=lambda refs, t: [],
        sources_metadata=lambda refs: [],
        src_collected=lambda: [],
        src_record_from_text=lambda t: None,
        usage_estimate=lambda p, c: {},
    )
    # Configure dag_exec
    de.configure(
        agent_registry={"hermes-worker": {"model": "hermes-3"}, "gpu-node": {"model": "gpu-model"}},
        slow_lanes=set(),
        kv_fork_enable=False,
        worker_tools_enable=False,
        request_cancel_enable=False,
        swarm_saturate=False
    )


def t_both_intent_deps():
    # 1. Multi-task "both" intent: research facet (web/news) + action facet (local_state)
    tasks = [
        {"title": "Research GPU settings", "web": True, "target_agent": "hermes-worker"},
        {"title": "Apply local config changes", "local_state": True, "target_agent": "gpu-node"}
    ]
    res = swarm._agent_dag_from_tasks(tasks, live_agents={"hermes-worker", "gpu-node"})
    nodes = res["nodes"]
    
    check("both-intent: two nodes built", len(nodes) == 2, str(len(nodes)))
    
    # Research node t1 should have deps=[]
    t1 = next(n for n in nodes if n["web"])
    check("both-intent: t1 is web", t1["web"] is True)
    check("both-intent: t1 deps empty", t1["deps"] == [])
    
    # Action node t2 should have deps=['t1']
    t2 = next(n for n in nodes if n["local_state"])
    check("both-intent: t2 is local", t2["local_state"] is True)
    check("both-intent: t2 depends on t1", t2["deps"] == [t1["id"]])


def t_parse_research_claims():
    # Test JSON parsing
    json_out = '[{"claim": "Gemma 2 is released", "source": "Google Blog"}]'
    claims1 = de.parse_research_claims(json_out)
    check("parse-claims: JSON array parsed", len(claims1) == 1, str(claims1))
    check("parse-claims: claim text correct", claims1[0]["claim"] == "Gemma 2 is released")
    check("parse-claims: source correct", claims1[0]["source"] == "Google Blog")

    # Test Markdown/fallback parsing
    text_out = "Claim: FakeGame 6 has a new teaser Source: Mock Games Website"
    claims2 = de.parse_research_claims(text_out)
    check("parse-claims: text line parsed", len(claims2) == 1, str(claims2))
    check("parse-claims: text claim text", claims2[0]["claim"] == "FakeGame 6 has a new teaser")
    check("parse-claims: text source", claims2[0]["source"] == "Mock Games Website")

    # Test bracket fallback
    bracket_out = "The CPU temperature is 45C [sys_logs] and fan is at 80% [hardware_monitor]."
    claims3 = de.parse_research_claims(bracket_out)
    check("parse-claims: bracket parsed", len(claims3) == 1, str(claims3))
    check("parse-claims: claim 1 text", claims3[0]["claim"] == "The CPU temperature is 45C  and fan is at 80% .")
    check("parse-claims: claim 1 source", claims3[0]["source"] == "sys_logs, hardware_monitor")


def t_execute_dag_node_ledger_writes():
    # Mock database functions
    created_queries = []
    fired_queries = []
    read_queries = []

    def mock_db_create(table, row, now_fields=None):
        created_queries.append((table, row, now_fields))
        return f"INSERT INTO {table} VALUES (...)"

    def mock_db_fire(sql):
        fired_queries.append(sql)

    def mock_db_post(sql):
        return sql

    async def mock_db_read(sql, pg_sql=None):
        read_queries.append(sql)
        if "fact_ledger" in sql:
            return [{"claim": "GPU temperature is 72C", "source": "nvidia-smi"}]
        return []

    # Inject mock helpers into dag_exec
    de.configure(
        db_create=mock_db_create,
        db_fire=mock_db_fire,
        db_post=mock_db_post,
        db_read=mock_db_read,
    )

    # Mock execute_dag_node_core to return success output
    async def mock_execute_dag_node_core(node, results_by_id, seen_actions, dag_summary, session_id, client, frag_q):
        # If it is a research node, return JSON text
        if node.get("web"):
            return {
                "success": True,
                "output": '[{"claim": "Gemma 2 has 27B params", "source": "nomic"}]',
                "latency_ms": 100,
                "tool": "agent:hermes-worker"
            }
        return {"success": True, "output": "applied changes", "latency_ms": 50}

    de._execute_dag_node_core = mock_execute_dag_node_core

    # Run research node execution
    res_node = {
        "id": "t1",
        "agent": "hermes-worker",
        "prompt": "Find Gemma 2 details",
        "web": True
    }
    asyncio.run(de._execute_dag_node(res_node, {}, {}, "summary", "session-123", None))

    check("ledger-writes: progress_ledger assigned logged",
          any(t == "progress_ledger" and r.get("state") == "assigned" for t, r, _ in created_queries))
    check("ledger-writes: progress_ledger completed logged",
          any(t == "progress_ledger" and r.get("state") == "completed" for t, r, _ in created_queries))
    check("ledger-writes: fact_ledger claim logged",
          any(t == "fact_ledger" and r.get("claim") == "Gemma 2 has 27B params" for t, r, _ in created_queries))

    # Clear lists
    created_queries.clear()
    fired_queries.clear()

    # Run action node execution to verify fact ledger read and prompt injection
    act_node = {
        "id": "t2",
        "agent": "hermes-worker",
        "prompt": "Optimize GPU settings",
        "local_state": True
    }
    asyncio.run(de._execute_dag_node(act_node, {}, {}, "summary", "session-123", None))

    check("ledger-writes: fact_ledger read on action node", len(read_queries) > 0)
    check("ledger-writes: facts injected into action prompt",
          "[Grounded Facts from Research]" in act_node["prompt"] and "GPU temperature is 72C" in act_node["prompt"])


def t_synthesis_reducer():
    # Configure database mock for synthesise
    async def mock_db_read(sql, pg_sql=None):
        if "fact_ledger" in sql:
            return [{"claim": "WSL memory is capped", "source": "wsl.conf"}]
        return []

    swarm.configure(db_read=mock_db_read)

    dag = {
        "summary": "synth-test",
        "nodes": [
            {"id": "t1", "agent": "hermes-worker", "web": True},
            {"id": "t2", "agent": "gpu-node", "local_state": True}
        ]
    }
    
    # Mock execute_dag_bounded
    async def mock_exec_bounded(dag_dict, *, session_id=None, request=None, **kwargs):
        return {
            "success": True,
            "node_results": [
                {"node_id": "t1", "tool": "agent:hermes-worker", "output": "claim details", "success": True},
                {"node_id": "t2", "tool": "agent:gpu-node", "output": "changes complete", "success": True}
            ]
        }
    swarm._execute_dag_bounded = mock_exec_bounded

    # Execute respond and grab the synthesise outcome
    # We will invoke respond_agent_dag and test it
    async def run_synth():
        # Wrap respond_agent_dag to get output of merged synthesis
        # We can also mock polish_response to inspect merged
        orig_polish = swarm.polish_response
        captured_merged = None
        async def mock_polish(prompt, model, **kwargs):
            nonlocal captured_merged
            captured_merged = prompt
            return "Polished synthesis answer"
        swarm.polish_response = mock_polish
        try:
            await swarm._respond_agent_dag(dag, {}, streaming=False, chat_id="chat-1", model="m", session_id="session-1", last_user_text="hi", persona_system="")
        finally:
            swarm.polish_response = orig_polish
        return captured_merged

    merged_prompt = asyncio.run(run_synth())
    
    check("synthesis: merged prompt non-empty", bool(merged_prompt))
    check("synthesis: research node has claims formatted",
          "Claims & Sources" in merged_prompt and "WSL memory is capped" in merged_prompt)
    check("synthesis: action node has verb-output schema",
          "Verb-Output Schema" in merged_prompt and "changes complete" in merged_prompt)


def t_replan_stall_trigger():
    # Mock db helpers
    created_events = []
    
    def mock_db_create(table, row, now_fields=None):
        if table == "event":
            created_events.append(row)
        return "INSERT INTO event VALUES (...)"

    def mock_db_fire(sql):
        pass
    def mock_db_post(sql):
        return sql

    async def mock_db_read(sql, pg_sql=None):
        # Return count=3 stalls to trigger the >2 condition
        return [{"c": 3}]

    swarm.configure(
        db_read=mock_db_read,
        db_create=mock_db_create,
        db_fire=mock_db_fire,
        db_post=mock_db_post,
        dag_replan_max=1
    )

    dag = {
        "summary": "stall-test",
        "nodes": [
            {"id": "t1", "agent": "hermes-worker", "web": True}
        ]
    }

    # Track execute_dag_bounded calls
    exec_calls = 0
    async def mock_exec_bounded(dag_dict, *, session_id=None, request=None, **kwargs):
        nonlocal exec_calls
        exec_calls += 1
        return {
            "success": True,
            "node_results": [
                {"node_id": "t1", "tool": "agent:hermes-worker", "output": "outcome", "success": True}
            ]
        }
    swarm._execute_dag_bounded = mock_exec_bounded

    asyncio.run(swarm._respond_agent_dag(dag, {}, streaming=False, chat_id="chat-1", model="m", session_id="session-1", last_user_text="hi", persona_system=""))

    check("replan-stall: execute_dag run twice due to replan", exec_calls == 2, str(exec_calls))
    check("replan-stall: replan event logged to DB",
          any("stall count is 3" in e.get("summary", "") for e in created_events))


def main():
    print("=== Running T-030 Dual-Ledger Tests ===")
    setup_test_stubs()
    t_both_intent_deps()
    t_parse_research_claims()
    t_execute_dag_node_ledger_writes()
    t_synthesis_reducer()
    t_replan_stall_trigger()
    print("=== T-030 Dual-Ledger Tests Done ===")
    sys.exit(1 if _fails > 0 else 0)

if __name__ == "__main__":
    main()

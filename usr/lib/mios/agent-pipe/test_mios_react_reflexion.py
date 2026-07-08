#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for T-031 (ReAct+Reflexion Durable Loop + Checkpoint-per-Superstep). Pure stdlib + asyncio, no server.py/DB/network. Verifies reflexion gate checks, reflexion retry event logging, superstep checkpoint saving/loading for both execute_dag and v1_secondary_tool_loop.
# AI-related: ./mios_pipe/routing/dag_exec.py, ./mios_pipe/routing/secondary_loop.py
# AI-functions: check, t_reflexion_gate, t_tool_failure_reflexion_flow, t_superstep_checkpoints, t_dag_execution_checkpoint_resume, main
"""Unit tests for T-031 ReAct+Reflexion Durable Loop + Checkpoint-per-Superstep."""

import asyncio
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)

import mios_pipe.routing.dag_exec as de
import mios_pipe.routing.secondary_loop as sl
import mios_toolexec

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, scripted_messages):
        self._q = list(scripted_messages)
        self.calls = 0

    async def post(self, url, content=None, headers=None, timeout=None):
        self.calls += 1
        msg = self._q.pop(0) if self._q else {"content": "done."}
        return _Resp({"choices": [{"message": msg}]})


def t_reflexion_gate():
    # Test checking [agent].reflexion_enable gate
    class FakeConfig:
        @staticmethod
        def _toml_section(section):
            if section in ("agent", "agents", "agent_pipe"):
                return {"reflexion_enable": "false"}
            return {}
            
    sys.modules["mios_config"] = FakeConfig

    import mios_reflect
    import mios_pipe.routing.reflect as mpr
    async def mock_reflect(*a, **k):
        return {"tool": "read_file", "args": {}, "rationale": "retry logic"}
    mpr.reflect_on_step_failure = mock_reflect
    sys.modules["mios_reflect"].__dict__["reflect_on_step_failure"] = mock_reflect
    
    db_reads = []
    async def mock_db_read(sql, pg_sql=None):
        db_reads.append(sql)
        return []

    sl.configure(
        secondary_tool_max_iters=2,
        secondary_replan_max=1,
        apply_outbound_auth=lambda *a: None,
        endpoint_supports_parallel_tools=lambda *a: False,
        db_read=mock_db_read
    )
    
    scripted = [
        {"tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
        {"content": "I am done."}
    ]
    client = _FakeClient(scripted)
    
    async def mock_exec_failed(tcs, push, allow_write=False):
        return [{"role": "tool", "content": '{"success": false, "error": "file not found"}', "tool_call_id": "call_1"}], True
        
    sl._exec_tool_calls = mock_exec_failed
    sl._rescue_tool_calls = lambda *a: []
    
    res_msgs = asyncio.run(sl._v1_secondary_tool_loop(
        client, "http://endpoint", "model-1", {}, [], [{"name": "read_file"}], 10, lambda *a: None,
        session_id="session-1"
    ))
    
    has_reflexion = any("SYSTEM REFLEXION" in str(m.get("content") or "") for m in res_msgs)
    check("reflexion-gate: reflexion disabled in config -> no reflexion prompt", not has_reflexion)


def t_tool_failure_reflexion_flow():
    class FakeConfig:
        @staticmethod
        def _toml_section(section):
            if section in ("agent", "agents", "agent_pipe"):
                return {"reflexion_enable": "true"}
            return {}
    sys.modules["mios_config"] = FakeConfig

    import mios_reflect
    import mios_pipe.routing.reflect as mpr
    async def mock_reflect(*a, **k):
        return {"tool": "read_file", "args": {}, "rationale": "retry logic"}
    mpr.reflect_on_step_failure = mock_reflect
    sys.modules["mios_reflect"].__dict__["reflect_on_step_failure"] = mock_reflect
    
    created_queries = []
    fired_queries = []
    
    def mock_db_create(table, row, now_fields=None):
        created_queries.append((table, row))
        return f"INSERT INTO {table} VALUES (...)"
        
    def mock_db_fire(sql):
        fired_queries.append(sql)
        
    def mock_db_post(sql):
        return sql
        
    async def mock_db_read(sql, pg_sql=None):
        return []
        
    sl.configure(
        secondary_tool_max_iters=3,
        secondary_replan_max=1,
        apply_outbound_auth=lambda *a: None,
        endpoint_supports_parallel_tools=lambda *a: False,
        db_read=mock_db_read,
        db_create=mock_db_create,
        db_fire=mock_db_fire,
        db_post=mock_db_post
    )
    
    scripted = [
        {"tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
        {"content": "Let me try another way."}
    ]
    client = _FakeClient(scripted)
    
    async def mock_exec_failed(tcs, push, allow_write=False):
        return [{"role": "tool", "content": '{"success": false, "error": "permission denied"}', "tool_call_id": "call_1"}], True
    sl._exec_tool_calls = mock_exec_failed
    
    res_msgs = asyncio.run(sl._v1_secondary_tool_loop(
        client, "http://endpoint", "model-1", {}, [], [{"name": "read_file"}], 10, lambda *a: None,
        session_id="session-100"
    ))
    
    event_logged = any(table == "event" and row.get("kind") == "reflexion_retry" for table, row in created_queries)
    check("reflexion-flow: logged reflexion_retry event", event_logged)
    
    has_reflexion = any("SYSTEM REFLEXION" in str(m.get("content") or "") for m in res_msgs)
    check("reflexion-flow: reflexion prompt injected into history", has_reflexion)


def t_superstep_checkpoints():
    created_queries = []
    fired_queries = []
    
    def mock_db_create(table, row, now_fields=None):
        created_queries.append((table, row))
        return f"INSERT INTO {table} VALUES (...)"
        
    def mock_db_fire(sql):
        fired_queries.append(sql)
        
    def mock_db_post(sql):
        return sql
        
    async def mock_db_read(sql, pg_sql=None):
        return []
        
    sl.configure(
        secondary_tool_max_iters=2,
        secondary_replan_max=1,
        apply_outbound_auth=lambda *a: None,
        endpoint_supports_parallel_tools=lambda *a: False,
        db_read=mock_db_read,
        db_create=mock_db_create,
        db_fire=mock_db_fire,
        db_post=mock_db_post
    )
    
    scripted = [
        {"tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
        {"content": "Finished."}
    ]
    client = _FakeClient(scripted)
    
    async def mock_exec_ok(tcs, push, allow_write=False):
        return [{"role": "tool", "content": '{"success": true}', "tool_call_id": "call_1"}], True
    sl._exec_tool_calls = mock_exec_ok
    
    asyncio.run(sl._v1_secondary_tool_loop(
        client, "http://endpoint", "model-1", {}, [], [{"name": "read_file"}], 10, lambda *a: None,
        session_id="session-react-1"
    ))
    
    ckpt_written = any(table == "session" and row.get("kind") == "checkpoint"
                       and "session-react-1" in row.get("id") for table, row in created_queries)
    check("superstep-checkpoints: saved superstep checkpoint to session table", ckpt_written)
    
    checkpoint_meta = next(row.get("meta") for table, row in created_queries if table == "session" and row.get("kind") == "checkpoint")
    check("superstep-checkpoints: checkpoint carries superstep index", "superstep_idx" in checkpoint_meta)
    check("superstep-checkpoints: checkpoint carries messages history", "messages" in checkpoint_meta)


def t_dag_execution_checkpoint_resume():
    created_queries = []
    fired_queries = []
    read_queries = []
    
    def mock_db_create(table, row, now_fields=None):
        created_queries.append((table, row))
        return f"INSERT INTO {table} VALUES (...)"
        
    def mock_db_fire(sql):
        fired_queries.append(sql)
        
    def mock_db_post(sql):
        return sql
        
    async def mock_db_read(sql, pg_sql=None):
        read_queries.append(sql)
        if "superstep_1" in sql:
            return [{
                "meta": {
                    "level_res": [{"success": True, "node_id": "t1", "output": "simulated from checkpoint", "tool": "agent:hermes-worker"}]
                }
            }]
        return []
        
    async def mock_get_client():
        return object()

    de.configure(
        db_read=mock_db_read,
        db_create=mock_db_create,
        db_fire=mock_db_fire,
        db_post=mock_db_post,
        agent_registry={"hermes-worker": {"model": "hermes-3"}, "gpu-node": {"model": "gpu-model"}},
        slow_lanes=set(),
        kv_fork_enable=False,
        worker_tools_enable=False,
        request_cancel_enable=False,
        swarm_saturate=False,
        get_client=mock_get_client,
        scratchpad_note=lambda *a, **k: None,
        sanitize_tool_text=lambda s: s
    )
    de._record_dag_node_row = lambda res, sid: None
    
    exec_nodes = []
    async def mock_exec_core(node, results_by_id, seen_actions, dag_summary, session_id, client, frag_q):
        exec_nodes.append(node["id"])
        return {"success": True, "output": "executed live", "tool": "agent:gpu-node", "node_id": node["id"]}
    de._execute_dag_node_core = mock_exec_core
    
    dag = {
        "summary": "resume-test",
        "nodes": [
            {"id": "t1", "agent": "hermes-worker", "deps": []},
            {"id": "t2", "agent": "gpu-node", "deps": ["t1"]}
        ]
    }
    
    res = asyncio.run(de.execute_dag(dag, session_id="session-dag-200"))
    
    check("dag-resume: did not execute t1 (read from checkpoint)", "t1" not in exec_nodes)
    check("dag-resume: executed t2 live", "t2" in exec_nodes)
    
    checkpoint_2_saved = any(table == "session" and "superstep_2" in row.get("id") for table, row in created_queries)
    check("dag-resume: saved level 2 checkpoint to session table", checkpoint_2_saved)


def main():
    print("=== Running T-031 ReAct/Reflexion Durable Loop Tests ===")
    t_reflexion_gate()
    t_tool_failure_reflexion_flow()
    t_superstep_checkpoints()
    t_dag_execution_checkpoint_resume()
    print("=== T-031 ReAct/Reflexion Durable Loop Tests Done ===")
    sys.exit(1 if _fails > 0 else 0)

if __name__ == "__main__":
    main()

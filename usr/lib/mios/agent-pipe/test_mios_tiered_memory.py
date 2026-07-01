#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for MEM-02 (tiered memory / context warning and eviction logic). Pure stdlib + asyncio, no live Letta server required. Runs as `python3 test_mios_tiered_memory.py` (exit 0 = pass).
# usr/lib/mios/agent-pipe/test_mios_tiered_memory.py

import sys
import os
import asyncio
import json
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mios_pipe.routing.chat as chat
import mios_compact
import mios_tokenize

_fails = 0

def check(name, cond, detail=""):
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))

class MockRequest:
    def __init__(self, body_dict, headers=None):
        self.body_dict = body_dict
        self.headers = headers or {}
        
    async def body(self):
        return json.dumps(self.body_dict).encode("utf-8")

def m(role, content):
    return {"role": role, "content": content}

# Setup spys
events_written = []
memories_written = []
scratch_written = []
scratchpads = {}

def mock_db_write(table, fields, **kwargs):
    if table == "event":
        events_written.append(fields)
    elif table == "agent_memory":
        memories_written.append(fields)
    elif table == "scratch":
        scratch_written.append(fields)

def mock_scratchpad_for(session_id):
    if session_id not in scratchpads:
        scratchpads[session_id] = deque()
    return scratchpads[session_id]

async def mock_embed_one(text):
    return [0.1] * 768

def mock_turn_tenant():
    return "test-tenant"

async def mock_summarize(evicted):
    return "Evicted turns summary"

async def test_warning_and_eviction():
    chat.LETTA_MEMORY_BACKEND = False
    chat._db_write = mock_db_write
    chat._embed_one = mock_embed_one
    chat._scratchpad_for = mock_scratchpad_for
    chat._turn_tenant = mock_turn_tenant
    chat._summarize_evicted_messages = mock_summarize
    chat.SCRATCHPAD_PERSIST = True
    chat.EMB_MODEL = "test-model"
    chat.EMB_VERSION = "test-version"
    import contextvars
    chat._conv_key_var = contextvars.ContextVar("conv_key", default="test-session")
    chat._turn_volatile_var = contextvars.ContextVar("volatile", default=False)
    chat._trace_id_var = contextvars.ContextVar("trace_id", default="")
    chat._span_id_var = contextvars.ContextVar("span_id", default="")
    chat._client_env_var = contextvars.ContextVar("client_env", default=None)
    chat._src_turn_var = contextvars.ContextVar("src_turn", default="")
    chat._sources_var = contextvars.ContextVar("sources", default=[])
    chat._routed_domain_var = contextvars.ContextVar("routed_domain", default=None)
    
    import json
    chat._loads_lenient = lambda text: json.loads(text) if text else {}
    chat._extract_last_user_text = lambda msgs: next((m["content"] for m in reversed(msgs) if isinstance(m, dict) and m.get("role") == "user"), "")
    chat._strip_owui_scaffold = lambda x: x
    chat._scratchpad_key = lambda b, f: "test-session"
    chat._src_turn_key = lambda: "test-turn-key"
    
    # Mock _toml_section to return a custom n_ctx (e.g. 50 tokens)
    # Mock _toml_section to return a custom n_ctx (e.g. 100 tokens)
    chat._toml_section = lambda sect: {"n_ctx": 100} if sect == "memory" else {}
    
    # Mock other required dependencies to pass-through
    chat._conv_key_var.set("test-session")
    
    async def _async_noop(*a, **k): return None
    chat._scratchpad_rehydrate = _async_noop
    chat._maybe_run_pending_approval = _async_noop
    chat._route_domain = _async_noop
    
    async def _async_admit(*a, **k): return (True, "")
    chat._budget_admit = _async_admit
    
    chat._seed_hop_from_headers = lambda *a, **k: None
    chat._src_turn_init = lambda *a, **k: None
    chat._client_env = lambda *a, **k: None
    
    async def _async_void(*a, **k): pass
    chat._vram_checkpoint = _async_void
    
    # 1. Test 70% threshold (between 70 and 100 tokens)
    msgs = [
        m("system", "You are an assistant."),
        m("user", "Hello " * 50) # ~75 tokens
    ]
    
    class MockKernel:
        def __init__(self):
            self.router = self
            self.dispatcher = self
            self.mode = "test"
        def route(self, refined):
            return self
        async def run(self, dec, **ctx):
            check("warning: event emitted", len(events_written) > 0)
            if events_written:
                check("warning: kind is context_warning", events_written[-1].get("kind") == "context_warning")
            
            last_msg = ctx.get("messages")[-1]
            check("warning: warning message appended", "WARNING" in last_msg.get("content"))
            raise RuntimeError("success_warning_test")
            
    chat._KERNEL = MockKernel()
    
    req = MockRequest({"model": "test", "messages": msgs})
    try:
        await chat.chat_completions_logic(req)
    except RuntimeError as e:
        if str(e) != "success_warning_test":
            raise
            
    # 2. Test 100% threshold eviction
    # Set n_ctx to 40 tokens so that the messages exceed 100%
    chat._toml_section = lambda sect: {"n_ctx": 40} if sect == "memory" else {}
    
    msgs_over = [
        m("system", "You are an assistant."),
        m("user", "Hello " * 10),  # ~15 tokens
        m("assistant", "Hi " * 10), # ~15 tokens
        m("user", "Hello " * 10),
        m("assistant", "Hi " * 10),
        m("user", "Hello " * 10),
        m("assistant", "Hi " * 10),
        m("user", "Hello " * 10),
    ]
    
    class MockKernelEvict:
        def __init__(self):
            self.router = self
            self.dispatcher = self
            self.mode = "test"
        def route(self, refined):
            return self
        async def run(self, dec, **ctx):
            scratch = mock_scratchpad_for("test-session")
            check("evict: scratchpad has summary prepended", len(scratch) > 0)
            if scratch:
                check("evict: system-summary is agent", scratch[0].get("agent") == "system-summary")
                check("evict: summary text in note", "Evicted turns summary" in scratch[0].get("note"))
                
            check("evict: scratch persistent write", len(scratch_written) > 0)
            check("evict: pgvector memory archival write", len(memories_written) > 0)
            if memories_written:
                check("evict: memory fact is summary", "Evicted turns summary" in memories_written[-1].get("fact"))
                check("evict: memory embedding added", memories_written[-1].get("emb") == [0.1] * 768)
                
            final_msgs = ctx.get("messages")
            check("evict: messages list rebuilt", len(final_msgs) > 0)
            check("evict: messages has summary system prompt", any("recursive summary" in str(m.get("content")).lower() for m in final_msgs))
            
            raise RuntimeError("success_evict_test")
            
    chat._KERNEL = MockKernelEvict()
    events_written.clear()
    memories_written.clear()
    scratch_written.clear()
    scratchpads.clear()
    
    req_evict = MockRequest({"model": "test", "messages": msgs_over})
    try:
        await chat.chat_completions_logic(req_evict)
    except RuntimeError as e:
        if str(e) != "success_evict_test":
            raise

def main():
    asyncio.run(test_warning_and_eviction())
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    sys.exit(1 if _fails else 0)

if __name__ == "__main__":
    main()

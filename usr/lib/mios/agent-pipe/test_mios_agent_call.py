#!/usr/bin/env python3
# AI-hint: Stdlib assert-script for mios_agent_call. Stubs every injected dep (no
# network/no admission/no broker -- async no-op gates, async-CM semaphores, a
# capturing fake httpx client) then drives _call_agent_complete end-to-end down the
# /v1 (non-ollama) path to assert (1) request-body ASSEMBLY (model/messages/tools/
# tool_choice preserved, stream=False, max_tokens defaulted, enable_thinking=False)
# and (2) response NORMALISATION -- the chrome-strip + think-tag-strip pipeline on a
# 200, and the error path (non-200 with no failover chain -> ('', dropped from the
# merge)). Run: python test_mios_agent_call.py
# AI-related: ./mios_agent_call.py
# AI-functions: (test)
"""Offline regression for mios_agent_call -- body assembly + response normalisation."""

import asyncio
import contextvars
import json

import mios_agent_call as T


# ── async-context-manager + async-no-op stubs (no network, no admission) ──
class _ACM:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _acm(*_a, **_k):
    return _ACM()


async def _anoop(*_a, **_k):
    return None


# ── a capturing fake httpx client ──────────────────────────────────
class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """Records the last POST + replays a scripted response."""

    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        self.calls = []

    async def post(self, url, *, content=None, headers=None, timeout=None):
        body = json.loads(content.decode("utf-8")) if content else {}
        self.calls.append({"url": url, "body": body, "headers": headers})
        return _Resp(self.status, self.payload)


# ── a capturing fake STREAMING httpx client ────────────────────────
class _StreamResp:
    """Async-CM SSE response: replays scripted `data:` lines via aiter_lines()."""

    def __init__(self, status, lines):
        self.status_code = status
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aiter_lines(self):
        for ln in self._lines:
            yield ln


class _FakeStreamClient:
    """Records the last client.stream() + replays a scripted SSE line list."""

    def __init__(self, status, lines):
        self.status = status
        self.lines = lines
        self.calls = []

    def stream(self, method, url, *, content=None, headers=None, timeout=None):
        body = json.loads(content.decode("utf-8")) if content else {}
        self.calls.append({"method": method, "url": url, "body": body,
                           "headers": headers})
        return _StreamResp(self.status, self.lines)


# ── inject stubs ───────────────────────────────────────────────────
_conv = contextvars.ContextVar("conv", default="")
_dispatch = contextvars.ContextVar("dispatch", default="")
_kvparent = contextvars.ContextVar("kvparent", default="")


def _configure(client_unused=None):
    T.configure(
        healthgate_connect_timeout=6.0,
        healthgate_read_timeout=120.0,
        secondary_tool_loop=False,   # skip the pipe-side tool-loop in this test
        kv_fork_enable=False,
        src_turn_header="X-MiOS-Turn",
        agent_registry={},
        sloshed=type("_SloShed", (Exception,), {}),
        admit=_anoop,
        agent_binding=lambda cfg, eng: (cfg.get("endpoint"), cfg.get("model")),
        agent_offload_engine=lambda cfg: None,
        apply_outbound_auth=lambda hdrs, ep: None,
        conv_key_var=_conv,
        current_trace_id=lambda: "",
        dispatch_agent_var=_dispatch,
        dispatch_priority=lambda cfg: 0.0,
        endpoint_sem=_acm,
        harvest_sub_sources=lambda rj, content: None,
        hop_via_headers=lambda: {},
        kv_fork_parent_var=_kvparent,
        lane_sem=_acm,
        lane_sem_key=lambda cfg: "cpu",
        model_active=_anoop,
        ollama_secondary_tool_loop=_anoop,
        opt_int_mb=lambda v: 0,
        priority_gate=_acm,
        # _num_predict_cap_for + _trip_breaker are now NATIVE to this module (moved
        # home from server.py -- the dispatch path is their sole caller). The cap fn
        # branches on the injected _is_slow_lane_ep probe + the SSOT ceilings: forced
        # slow here so max_tokens defaults to the CPU cap (512), preserving the body-
        # assembly assertions. _trip_breaker is a no-op on these tests because
        # should_health_probe is stubbed False (it never writes _NODE_LIVE); the
        # dedicated block below covers both functions directly.
        is_slow_lane_ep=lambda ep: True,
        ollama_num_predict_cap=2048,
        ollama_num_predict_cap_cpu=512,
        node_live={},
        # _record_cost is now NATIVE to this module (moved home from server.py). It
        # stays a no-op on these dispatch tests because cost_accounting_enable
        # defaults OFF (so it returns before touching the ledger). Its own coverage
        # is the dedicated [_record_cost cost accounting] block below.
        # _kv_paging / _kv_fork / _rr_eligible / _rr_run are now NATIVE to this
        # module (moved home from server.py). They stay inert on this dispatch
        # path: KV_PAGING_ENABLE / KV_FORK_ENABLE / RR_ENABLE all default OFF, so
        # _rr_eligible returns False (semaphore path) and the _kv_paging bracket
        # is a zero-op yield -- no stubs needed for the _call_agent_complete tests.
        should_health_probe=lambda cfg: False,
        src_turn_key=lambda: "",
        # strip_agent_chrome / strip_think_tags: small real-ish strippers so we
        # actually exercise the normalisation pipeline.
        strip_agent_chrome=lambda t: t.replace("> build · qwen\n", "").strip(),
        strip_think_tags=lambda t: t.replace("<think>x</think>", ""),
        v1_secondary_tool_loop=_anoop,
    )
    # _endpoint_is_ollama is a direct sibling import; force the /v1 (non-native)
    # branch so the test doesn't depend on mios_endpoints port heuristics.
    T._endpoint_is_ollama = lambda ep, cfg, eng=None: False


_configure()

PASS = 0


def ok(cond, label):
    global PASS
    assert cond, "FAIL: " + label
    PASS += 1
    print("  ok:", label)


CFG = {"endpoint": "http://gw:8642/v1", "model": "mios-secondary"}
BODY = {
    "messages": [{"role": "user", "content": "hi"}],
    "tools": [{"type": "function", "function": {"name": "web_search"}}],
    "tool_choice": "auto",
}


# ── happy path: body assembly + normalisation on a 200 ──────────────
print("[request-body assembly + normalisation]")


async def _happy():
    client = _FakeClient(200, {"choices": [{"message": {
        "content": "> build · qwen\n<think>x</think>the real answer"}}]})
    name, text = await T._call_agent_complete(
        "secondary", CFG, dict(BODY), {}, client, prefer_cpu=True)
    ok(len(client.calls) == 1, "exactly one /v1 POST issued")
    call = client.calls[0]
    ok(call["url"] == "http://gw:8642/v1/chat/completions",
       "POST targets the agent's bound /v1 endpoint")
    b = call["body"]
    ok(b["model"] == "mios-secondary", "body carries the agent's model")
    ok(b["messages"] == BODY["messages"], "body preserves the messages verbatim")
    ok(b["tools"] == BODY["tools"], "body preserves the offered tools")
    ok(b["tool_choice"] == "auto", "body preserves tool_choice")
    ok(b["stream"] is False, "stream forced False (non-streaming dispatch)")
    ok(b["max_tokens"] == 512, "max_tokens defaulted from _num_predict_cap_for")
    ok(b.get("chat_template_kwargs") == {"enable_thinking": False},
       "thinking channel disabled so /v1 renders content not reasoning")
    ok("options" not in b and "think" not in b,
       "ollama-only options/think stripped from the /v1 body")
    # normalisation: chrome line + think tags both stripped from the answer
    ok(name == "secondary", "returns the dispatched agent name")
    ok(text == "the real answer",
       "response normalised: agent-chrome + think tags stripped")


asyncio.run(_happy())


# ── error path: non-200 with no failover chain -> dropped from merge ──
print("[error path]")


async def _err():
    client = _FakeClient(500, {"error": "boom"})
    name, text = await T._call_agent_complete(
        "secondary", CFG, dict(BODY), {}, client, prefer_cpu=True)
    ok(name == "secondary" and text == "",
       "non-200 with no failover_agents -> ('', dropped from the merge)")


asyncio.run(_err())


# ── inner failover: empty endpoint with no chain -> '' ──────────────
print("[no-endpoint guard]")


async def _noep():
    client = _FakeClient(200, {"choices": []})
    name, text = await T._call_agent_complete(
        "secondary", {"endpoint": "", "model": "m"}, dict(BODY), {}, client)
    ok(text == "", "absent endpoint with no failover -> '' (skipped)")
    ok(len(client.calls) == 0, "no POST issued when the endpoint is empty")


asyncio.run(_noep())


# ── streaming sibling: SSE fragments broadcast onto the merge queue ──
# _call_agent_stream_inner streams a secondary's output, pushing ("SF", name,
# fragment) onto the shared queue `q` AS fragments arrive (live reasoning
# broadcast into the council think-dropdown -- streaming is proof of function),
# while folding only the ANSWER content into the returned merge text.
print("[streaming: live fragment broadcast + merge text]")


async def _stream_happy():
    # content + reasoning_content interleaved; reasoning streams to the dropdown
    # but is NOT folded into the merge text; <think> tags stripped from the merge.
    lines = [
        "",                                                  # blank -> skipped
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"reasoning_content":" pondering"}}]}',
        'data: {"choices":[{"delta":{"content":" <think>x</think>world"}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":" AFTER-DONE"}}]}',  # past [DONE]
    ]
    client = _FakeStreamClient(200, lines)
    q = asyncio.Queue()
    name, text = await T._call_agent_stream_inner(
        "secondary", CFG, dict(BODY), {}, client, q, prefer_cpu=True)
    ok(len(client.calls) == 1, "exactly one client.stream() issued")
    call = client.calls[0]
    ok(call["url"] == "http://gw:8642/v1/chat/completions",
       "stream targets the agent's bound /v1 endpoint")
    b = call["body"]
    ok(b["stream"] is True, "stream forced True (streaming dispatch)")
    ok(b["model"] == "mios-secondary", "body carries the agent's model")
    ok(b["max_tokens"] == 512, "max_tokens defaulted from _num_predict_cap_for")
    ok(b.get("chat_template_kwargs") == {"enable_thinking": False},
       "thinking channel disabled so /v1 renders content not reasoning")
    ok("options" not in b and "think" not in b,
       "ollama-only options/think stripped from the /v1 body")
    # drain the broadcast queue
    frags = []
    while not q.empty():
        frags.append(q.get_nowait())
    ok(all(ev[0] == "SF" and ev[1] == "secondary" for ev in frags),
       "every queued event tagged ('SF', agent_name, fragment)")
    pushed = [ev[2] for ev in frags]
    ok(pushed == ["Hello", " pondering", " <think>x</think>world"],
       "both answer AND reasoning fragments broadcast live, in arrival order")
    # merge text: only content folds in, reasoning excluded, think tags stripped,
    # nothing past [DONE] consumed
    ok(name == "secondary", "returns the dispatched agent name")
    ok(text == "Hello world",
       "merge text = answer content only (reasoning excluded, <think> stripped, "
       "stops at [DONE])")


asyncio.run(_stream_happy())


# ── streaming error path: non-200 -> dropped from the merge ──────────
print("[streaming error path]")


async def _stream_err():
    client = _FakeStreamClient(500, ['data: {"choices":[{"delta":{"content":"x"}}]}'])
    q = asyncio.Queue()
    name, text = await T._call_agent_stream_inner(
        "secondary", CFG, dict(BODY), {}, client, q, prefer_cpu=True)
    ok(name == "secondary" and text == "",
       "non-200 stream -> ('', dropped from the merge)")
    ok(q.empty(), "no fragments broadcast on a non-200 stream")


asyncio.run(_stream_err())


# ── streaming no-endpoint guard: absent binding -> '' (skipped) ──────
print("[streaming no-endpoint guard]")


async def _stream_noep():
    client = _FakeStreamClient(200, [])
    q = asyncio.Queue()
    name, text = await T._call_agent_stream_inner(
        "secondary", {"endpoint": "", "model": "m"}, dict(BODY), {}, client, q)
    ok(text == "", "absent endpoint -> '' (skipped, streaming)")
    ok(len(client.calls) == 0, "no stream issued when the endpoint is empty")


asyncio.run(_stream_noep())


# ── moved engine actors: KV-paging/fork + RR-preemptible decode ──────
# These moved verbatim into mios_agent_call (their only caller was
# _call_agent_complete_inner). Pure + inert paths first (all flags default OFF),
# then the active paths with fakes for the /slots client + the priority gate.
print("[moved cluster: pure + inert paths]")

# _kv_base: strip a trailing /v1, else strip a trailing slash.
ok(T._kv_base("http://h:8080/v1") == "http://h:8080", "_kv_base strips a trailing /v1")
ok(T._kv_base("http://h:8080/") == "http://h:8080", "_kv_base strips a trailing slash")
ok(T._kv_base("http://h:8080") == "http://h:8080", "_kv_base leaves a bare root")

# _kv_filename: filesystem-safe + deterministic (SSOT with mios_kvfork).
_fn = T._kv_filename("conv/../x y")
ok(isinstance(_fn, str) and "/" not in _fn and "\\" not in _fn,
   "_kv_filename is filesystem-safe")
ok(T._kv_filename("conv-abc") == T._kv_filename("conv-abc"),
   "_kv_filename is deterministic for one conversation")

# _rr_eligible: RR_ENABLE defaults OFF -> never eligible.
ok(T._rr_eligible({"messages": [{"role": "user", "content": "hi"}]},
                  "http://h/v1", {}, None) is False,
   "_rr_eligible False while RR_ENABLE is off")


async def _kv_paging_inert():
    # KV_PAGING_ENABLE defaults OFF -> the bracket is a zero-op yield.
    client = _FakeClient(200, {})
    async with T._kv_paging(client, "http://h/v1", {"model": "m"}, None):
        pass
    ok(len(client.calls) == 0, "_kv_paging is a no-op yield when disabled")


asyncio.run(_kv_paging_inert())


async def _kv_fork_disabled():
    res = await T._kv_fork(_FakeClient(200, {}), "http://h/v1", {}, None,
                           "parent", "child")
    ok(res.get("forked") is False, "_kv_fork inert (disabled) -> forked False")


asyncio.run(_kv_fork_disabled())


# ── active paths: enable the KV/RR knobs + inject a /slots client/gate ──
print("[moved cluster: active KV-paging + RR decode]")


class _SlotResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http %d" % self.status_code)

    def json(self):
        return self._payload


class _SlotClient:
    """Fake llama.cpp client for /slots + /chat/completions (records calls)."""

    def __init__(self, status=200):
        self.status = status
        self.calls = []

    async def post(self, url, *, params=None, content=None, headers=None,
                   timeout=None):
        self.calls.append({
            "url": url, "params": params,
            "body": json.loads(content.decode("utf-8")) if content else {}})
        return _SlotResp(self.status, {"choices": [{
            "message": {"content": "sliced answer"},
            "finish_reason": "stop"}]})


class _FakeGate:
    def __init__(self):
        self.acquired = 0
        self.released = 0

    async def acquire(self, prio):
        self.acquired += 1

    def release(self):
        self.released += 1

    def head_priority(self):
        return None


_gate = _FakeGate()
T.configure(kv_paging_enable=True, kv_paging_slot=0, kv_paging_timeout=12.0,
            rr_enable=True, priority_queue_enable=True,
            kv_locks={}, kv_resident={}, backend_key="",
            global_priority_gate=_gate)
# force the /slots-lane branch without depending on mios_endpoints heuristics
T._endpoint_is_llamacpp = lambda ep, cfg, eng=None: True

# _rr_eligible now True for a plain completion, False once tools[] appear.
ok(T._rr_eligible({"messages": [{"role": "user", "content": "hi"}]},
                  "http://h/v1", {}, None) is True,
   "_rr_eligible True for a plain completion on a /slots lane")
ok(T._rr_eligible({"messages": [{"role": "user", "content": "hi"}],
                   "tools": [{"type": "function"}]},
                  "http://h/v1", {}, None) is False,
   "_rr_eligible False when the dispatch carries tools[]")


async def _slot_action_status():
    ok(await T._kv_slot_action(_SlotClient(200), "http://h/v1", "save",
                               "conv1", "m") is True,
       "_kv_slot_action True on a 200 slot save")
    ok(await T._kv_slot_action(_SlotClient(404), "http://h/v1", "restore",
                               "conv1", "m") is False,
       "_kv_slot_action False when every slot URL 404s")


asyncio.run(_slot_action_status())


async def _kv_paging_active():
    # cold slot -> page THIS conversation in (one restore), resident updated.
    T._KV_RESIDENT.clear()
    _conv.set("convA")
    client = _SlotClient(200)
    async with T._kv_paging(client, "http://h/v1", {"model": "m"}, None):
        pass
    ok(any(c["params"] == {"action": "restore"} for c in client.calls),
       "_kv_paging pages the conversation IN on a cold slot")
    key = T._kv_base("http://h/v1") + "#0"
    ok(T._KV_RESIDENT.get(key) == "convA",
       "_kv_paging records the resident conversation for the slot")


asyncio.run(_kv_paging_active())


async def _rr_run_single_slice():
    client = _SlotClient(200)
    text = await T._rr_run(client, "http://h/v1", "m",
                           [{"role": "user", "content": "hi"}],
                           conv="convA", priority=5.0, max_tokens=10)
    ok(text == "sliced answer", "_rr_run returns the assembled slice text")
    ok(_gate.acquired >= 1 and _gate.released == _gate.acquired,
       "_rr_run balances the priority gate (acquire == release)")


asyncio.run(_rr_run_single_slice())


# ── _record_cost: WS-RES-GOV per-dispatch recorder (moved home; tokenizer seam) ──
# Verifies the strangler move: it records into the injected server-owned ledger,
# its token total comes from the mios_tokenize seam (NOT an inline `// 4`), it
# attributes to the injected lane key, and it is a degrade-open no-op when the
# accounting flag is off. Synthetic fixed-length content (no baked example words)
# keeps the token estimate deterministic.
print("[_record_cost cost accounting]")
import time as _time
import mios_cost
import mios_tokenize

_ledger = mios_cost.CostLedger()
_model = mios_cost.CostModel(gpu_watts=300.0, usd_per_kwh=0.0)
T.configure(
    cost_accounting_enable=True,
    cost_ledger=_ledger,
    cost_model=_model,
    is_remote_endpoint=lambda ep: False,
    lane_sem_key=lambda cfg: "synthlane",
)
_cbody = {"messages": [{"role": "user", "content": "x" * 40}]}   # 40 synthetic chars
_ctext = "y" * 20                                                # 20 synthetic chars
_expect_tokens = (mios_tokenize.count_messages(_cbody["messages"])
                  + mios_tokenize.count_text(_ctext))
T._record_cost({"endpoint": "ep"}, "http://ep/v1", _time.time() - 1.0, _cbody, _ctext)
_snap = _ledger.snapshot()
ok(_snap["dispatches"] == 1, "_record_cost records exactly one dispatch")
ok(_snap["tokens"] == _expect_tokens,
   "_record_cost token total comes from the mios_tokenize seam (not inline //4)")
ok(_snap["by_lane"].get("synthlane", {}).get("n") == 1,
   "_record_cost attributes the dispatch to the injected lane key")

# Flag-gated + degrade-open: disabled => pure no-op (ledger untouched).
T.configure(cost_accounting_enable=False)
T._record_cost({"endpoint": "ep"}, "http://ep/v1", _time.time(), _cbody, _ctext)
ok(_ledger.snapshot()["dispatches"] == 1,
   "_record_cost is a no-op when cost_accounting_enable is off")


print("\nALL %d ASSERTIONS PASSED" % PASS)

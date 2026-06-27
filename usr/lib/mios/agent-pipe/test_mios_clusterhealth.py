# AI-hint: Stdlib unit test for mios_clusterhealth -- the cluster/scheduler/health route LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). Stubs every injected dep via configure() plus the runtime-reassigned lane resolver (sys.modules["mios_lanes_resolver"]._lane_resolver_current) with no network / no DB, then asserts each moved *_logic still produces the byte-shape the @app thin wrappers used to: cluster_health_logic (per-agent effective_up/failover_only rollup + lane_resolver snapshot via the getter), scheduler_state_logic (per-lane concurrency + admission/priority/kernel posture object), and health_logic (capability/health rollup -- backend/router/dci/security/passport blocks). Run: python test_mios_clusterhealth.py
# AI-related: ./mios_clusterhealth.py, ./server.py
# AI-functions: main
"""Stdlib unit tests for mios_clusterhealth (refactor ROUTE-SURFACE) -- stubbed, no I/O."""

import asyncio
import json
import sys
import types

import mios_clusterhealth as M

# Capture the REAL (native) helper-fn objects BEFORE any configure() override, so
# their dedicated tests exercise the moved-home implementations regardless of the
# stubs the *_logic tests later inject over the same names.
_REAL_PROBE = M._probe_one_endpoint
_REAL_LANE_SCHED = M._lane_sched_stats
_REAL_KERNEL_DETAIL = M._kernel_managers_detail
_REAL_FAILOVER = M._resolve_failover_chain


_fails = 0


class _FakeResp:
    """Minimal stand-in for an httpx response (status_code + .json())."""

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    """Async client whose .get(url) is routed through a handler -- no network."""

    def __init__(self, handler):
        self._handler = handler

    async def get(self, url, **kwargs):
        return self._handler(url, **kwargs)


def check(name, ok, detail=""):
    global _fails
    if ok:
        print(f"[PASS] {name}")
    else:
        _fails += 1
        print(f"[FAIL] {name} :: {detail}")


def _body(resp):
    """Decode a fastapi JSONResponse rendered body into a dict."""
    return json.loads(bytes(resp.body).decode("utf-8"))


# -- lane-resolver getter stub (the deferred landmine) --------------------
# cluster_health_logic reads the LIVE resolver via
# sys.modules["mios_lanes_resolver"]._lane_resolver_current(). Replace that module
# with a tiny fake so the moved body resolves the getter without the real lane
# infrastructure -- proving the getter access works post-extraction.
class _FakeResolver:
    def snapshot(self):
        return {"engine": "heavy", "cooldown": 0}


def _install_resolver(current):
    fake = types.ModuleType("mios_lanes_resolver")
    fake._lane_resolver_current = lambda: current
    sys.modules["mios_lanes_resolver"] = fake


# -- stub callables -------------------------------------------------------
_REGISTRY = {
    "hermes": {"role": "gateway", "default": True, "enabled": True,
               "endpoint": "http://hermes:8642", "model": "m"},
    "opencode": {"role": "coder", "default": False, "enabled": True,
                 "endpoint": "http://opencode:8633", "model": "c"},
    "disabled_peer": {"role": "x", "default": False, "enabled": False,
                      "endpoint": "http://x:9", "model": "z"},
}


def _resolve_failover_chain(name):
    # primary only -> single-hop chains (so SPOF/failover branches are exercised).
    cfg = _REGISTRY[name]
    return [{"name": name, "endpoint": cfg["endpoint"],
             "model": cfg["model"], "kind": "primary"}]


def _probe_results(name):
    # hermes + opencode reachable; the disabled peer's endpoint is down.
    return name != "disabled_peer"


async def _probe_one_endpoint(client, ep, timeout_s=3.0):
    up = ep not in ("http://x:9",)
    return (up, ["model-a", "model-b"] if up else [], 12 if up else 0)


def _agent_lane(cfg):
    return "gpu"


class _Gate:
    def stats(self):
        return {"queued": 0, "in_flight": 1, "cap": 3}


class _Tracer:
    def stats(self):
        return {"buffered": 0, "enabled": True}

    def recent(self, n):
        return []


class _Conflict:
    def stats(self):
        return {"serialized": [], "in_flight": 0}


class _Preempt:
    def stats(self):
        return {"suspended": 0, "free_slots": 3}


class _Ledger:
    def over_budget(self, b):
        return False

    def snapshot(self):
        return {"wh": 0.0, "usd": 0.0, "tokens": 0}


_KERNEL = types.SimpleNamespace(
    managers=lambda: {"scheduler": True, "memory": True},
    dispatcher=types.SimpleNamespace(modes=lambda: ["dag", "chat", "agent"]),
)


def _configure_common():
    M.configure(
        # cluster_health deps
        _AGENT_REGISTRY=_REGISTRY,
        _resolve_failover_chain=_resolve_failover_chain,
        _probe_one_endpoint=_probe_one_endpoint,
        _agent_lane=_agent_lane,
        # scheduler_state deps
        _lane_sched_stats=lambda: [{"lane": "gpu", "cap": 3, "in_flight": 1,
                                    "available": 2, "queued": 0}],
        AGENT_CONCURRENCY=3,
        _PG_PRIMARY=True,
        ADMIT_ENABLE=False,
        _over_global_ceiling=lambda: False,
        ADMIT_LOAD_CEIL=8.0,
        ADMIT_MEM_PCT=90.0,
        _host_stats_cached=lambda: {"load": 0.1, "mem_pct": 33.0},
        PRIORITY_QUEUE_ENABLE=False,
        PRIORITY_STARVATION_S=30.0,
        _GLOBAL_PRIORITY_GATE=_Gate(),
        KV_FORK_ENABLE=False,
        KV_PAGING_ENABLE=True,
        KV_PAGING_SLOT=0,
        KV_FORK_MAX_BRANCHES=4,
        _KV_RESIDENT={},
        KNOWLEDGE_EVICT_ENABLE=False,
        KNOWLEDGE_EVICT_DRYRUN=True,
        KNOWLEDGE_EVICT_INTERVAL_S=3600,
        KNOWLEDGE_EVICT_TTL_DAYS=30,
        KNOWLEDGE_EVICT_MAX_ROWS=1000,
        KNOWLEDGE_EVICT_BATCH=100,
        _TOOL_CONFLICT=_Conflict(),
        _TRACER=_Tracer(),
        RR_ENABLE=False,
        RR_QUANTUM_S=0.5,
        RR_SLICE_TOKENS=256,
        _PREEMPT=_Preempt(),
        BATCH_ENABLE=False,
        BATCH_INTERVAL_S=0.05,
        BATCH_MAX_SIZE=8,
        BATCH_NATIVE_HINTS=[],
        SMARTROUTE_ENABLE=False,
        SMARTROUTE_BUDGET=2,
        SLO_SHED_ENABLE=False,
        COST_ACCOUNTING_ENABLE=False,
        COST_BUDGET_USD=0.0,
        _COST_LEDGER=_Ledger(),
        _KERNEL=_KERNEL,
        _kernel_managers_detail=lambda: {"scheduler": {"queued": 0}},
        KERNEL_ROUTE=False,
        # health deps
        app=types.SimpleNamespace(version="9.9.9-test"),
        _ALLOWLIST_HOSTS={"localhost", "127.0.0.1"},
        _HIGH_PRIVILEGE_VERBS={"shell_exec", "container_restart"},
        _HIGH_PRIVILEGE_CURATED={"shell_exec"},
        _TAINT_VERBS={"web_extract"},
        _toml_section=lambda s: ({"firewall_high_privilege_verbs": ["container_restart"]}
                                 if s == "security" else {}),
        _passport_load_priv=lambda: None,
        _passport_kid=lambda: "kid-test",
        SKILLS_ENABLED=True,
        SKILLS_MIN_LENGTH=10,
        SKILLS_MAX_LENGTH=4000,
        SKILLS_MIN_SUPPORT=2,
        SKILLS_WINDOW_HOURS=168,
        SKILLS_AUTO_PROMOTE_THRESHOLD=5,
        PASSPORT_ENABLE=False,
        PASSPORT_ALGO="EdDSA",
        PASSPORT_AGENT_NAME="MiOS AI",
        PASSPORT_KEY_DIR="/var/lib/mios/ai/passport",
        PASSPORT_VERIFY_ON_READ=False,
        LAUNCHER_SOCK="/nonexistent/mios-launch.sock",
        DB_URL="http://localhost:8000",
    )


def t_probe_one_endpoint():
    # Native helper moved home from server.py. client is an ARGUMENT -> a fake
    # client routes every .get through a handler, so there is zero network.
    M.configure(_probe_auth_headers=lambda ep: {"Authorization": "Bearer t"})
    # OpenAI /v1/models success.
    r, lm, ms = asyncio.run(_REAL_PROBE(
        _FakeClient(lambda url, **k: _FakeResp(200, {"data": [{"id": "m1"},
                                                              {"id": "m2"}]})),
        "http://ep/v1"))
    check("probe: openai /models reachable + ids", r is True and lm == ["m1", "m2"])
    check("probe: latency_ms is int", isinstance(ms, int) and ms >= 0)
    # Empty endpoint short-circuits to down with zero latency.
    r0, lm0, ms0 = asyncio.run(_REAL_PROBE(_FakeClient(lambda url, **k: None), ""))
    check("probe: empty ep -> (False,[],0)", r0 is False and lm0 == [] and ms0 == 0)
    # Both transports raise -> unreachable.

    def _raise(url, **k):
        raise RuntimeError("conn refused")
    rd, lmd, _ = asyncio.run(_REAL_PROBE(_FakeClient(_raise), "http://dead/v1"))
    check("probe: unreachable -> down", rd is False and lmd == [])
    # ollama /api/tags fallback when /models is unavailable.

    def _tags(url, **k):
        if url.endswith("/api/tags"):
            return _FakeResp(200, {"models": [{"name": "n1"}]})
        raise RuntimeError("no openai surface")
    rt, lmt, _ = asyncio.run(_REAL_PROBE(_FakeClient(_tags), "http://ep/v1"))
    check("probe: ollama /api/tags fallback", rt is True and lmt == ["n1"])


def t_lane_sched_stats():
    # Native helper moved home from server.py -- reads the injected live lane
    # semaphore map; introspects available/in-flight/queued per lane.
    sems = {"gpu": asyncio.Semaphore(3), "cpu": asyncio.Semaphore(2)}
    M.configure(_LANE_SEMS=sems, AGENT_CONCURRENCY=4)
    by = {r["lane"]: r for r in _REAL_LANE_SCHED()}
    check("lane: both lanes present (sorted introspection)",
          set(by) == {"cpu", "gpu"})
    check("lane: gpu available == idle permits", by["gpu"]["available"] == 3)
    check("lane: gpu queued == 0 (no waiters)", by["gpu"]["queued"] == 0)
    check("lane: in_flight == cap - available",
          by["gpu"]["in_flight"] == max(0, by["gpu"]["cap"] - 3)
          and isinstance(by["gpu"]["cap"], int))


def t_kernel_managers_detail():
    # Native helper moved home from server.py -- rolls up the live kernel seams.
    M.configure(
        _GLOBAL_PRIORITY_GATE=_Gate(),
        _PREEMPT=_Preempt(),
        _MEMORY=types.SimpleNamespace(),
        _PG_PRIMARY=True,
        KV_PAGING_ENABLE=True,
        _VERB_CATALOG={"a": 1, "b": 2, "c": 3},
        _PERMISSION_TIERS={"public", "user", "admin"},
    )
    d = _REAL_KERNEL_DETAIL()
    check("kernel: scheduler seam from gate.stats()",
          d["scheduler"] == {"queued": 0, "in_flight": 1, "cap": 3})
    check("kernel: memory provider type name + pg_primary",
          d["memory"]["provider"] == "SimpleNamespace"
          and d["memory"]["pg_primary"] is True)
    check("kernel: context kv_paging", d["context"]["kv_paging"] is True)
    check("kernel: tools verb count", d["tools"]["verbs"] == 3)
    check("kernel: access pdp + tiers",
          d["access"]["pdp"] is True
          and set(d["access"]["tiers"]) == {"public", "user", "admin"})


def t_resolve_failover_chain():
    # Native helper moved home from server.py -- expands an agent name into its
    # full failover chain from the injected-by-reference _AGENT_REGISTRY. Synthetic
    # agent tokens only (no baked example words); assert the module's own structural
    # kind vocabulary (primary/failover/cpu-twin).
    reg = {
        # primary with one declared failover + a distinct cpu twin + a self-loop and
        # a dangling failover ref (both must be skipped).
        "a0": {"endpoint": "http://h0/v1", "model": "m0",
               "cpu_endpoint": "http://h0cpu", "cpu_model": "m0cpu",
               "failover_agents": ["a1", "a0", "ghost"]},
        "a1": {"endpoint": "http://h1/v1", "model": "m1"},
        # cpu_endpoint identical to endpoint -> NOT added as a cpu twin.
        "a2": {"endpoint": "http://h2", "model": "m2", "cpu_endpoint": "http://h2"},
    }
    M.configure(_AGENT_REGISTRY=reg)

    chain = _REAL_FAILOVER("a0")
    kinds = [h["kind"] for h in chain]
    check("failover: chain kinds primary->failover->cpu-twin",
          kinds == ["primary", "failover", "cpu-twin"], str(kinds))
    check("failover: self-loop + dangling ref skipped (one failover only)",
          [h["name"] for h in chain] == ["a0", "a1", "a0.cpu"],
          str([h["name"] for h in chain]))
    check("failover: cpu twin carries cpu_model + cpu_endpoint",
          chain[2]["model"] == "m0cpu" and chain[2]["endpoint"] == "http://h0cpu")

    # cpu_endpoint == endpoint -> no cpu twin appended.
    chain2 = _REAL_FAILOVER("a2")
    check("failover: cpu_endpoint==endpoint adds no twin",
          [h["kind"] for h in chain2] == ["primary"], str(chain2))

    # unknown agent -> empty chain (no crash).
    check("failover: unknown agent -> []", _REAL_FAILOVER("nope") == [])


def t_cluster_health():
    _install_resolver(_FakeResolver())
    _configure_common()
    b = _body(asyncio.run(M.cluster_health_logic()))
    check("cluster: object", b["object"] == "mios.cluster.health")
    names = {a["name"]: a for a in b["agents"]}
    check("cluster: all 3 agents present", set(names) ==
          {"hermes", "opencode", "disabled_peer"}, str(set(names)))
    check("cluster: hermes effective_up", names["hermes"]["effective_up"] is True)
    check("cluster: disabled_peer down", names["disabled_peer"]["effective_up"] is False)
    check("cluster: single_point_of_failure flagged (single primary hop)",
          names["hermes"]["single_point_of_failure"] is True)
    # council honesty: only ENABLED non-default + effective_up peers count.
    check("cluster: council_peers_up == 1 (opencode only)", b["council_peers_up"] == 1,
          str(b["council_peers_up"]))
    check("cluster: mode is council", b["mode"] == "council")
    check("cluster: lane_resolver snapshot via getter",
          b["lane_resolver"] == {"engine": "heavy", "cooldown": 0})
    check("cluster: agents_up == 2", b["agents_up"] == 2, str(b["agents_up"]))
    # resolver None -> lane_resolver None branch
    _install_resolver(None)
    b2 = _body(asyncio.run(M.cluster_health_logic()))
    check("cluster: lane_resolver None when resolver unbuilt",
          b2["lane_resolver"] is None)


def t_scheduler_state():
    _install_resolver(_FakeResolver())
    _configure_common()
    b = _body(asyncio.run(M.scheduler_state_logic()))
    check("sched: object", b["object"] == "mios.scheduler")
    check("sched: lanes from _lane_sched_stats",
          b["lanes"][0]["lane"] == "gpu" and b["lanes"][0]["cap"] == 3)
    check("sched: global_cap", b["global_cap"] == 3)
    check("sched: admission posture present",
          b["admission"]["enabled"] is False and b["admission"]["load_ceil"] == 8.0)
    check("sched: recall reflects _PG_PRIMARY (pgvector)",
          "pgvector" in b["memory_manager_tiers"]["recall"])
    check("sched: priority_gate merges gate stats",
          b["priority_gate"]["enabled"] is False and b["priority_gate"]["in_flight"] == 1)
    check("sched: kv_fork resident_slots", b["kv_fork"]["resident_slots"] == 0)
    check("sched: kernel modes from dispatcher",
          b["kernel"]["modes"] == ["dag", "chat", "agent"])
    check("sched: kernel shadow_route", b["kernel"]["shadow_route"] is False)
    check("sched: slo classes wired", "classes" in b["slo"])
    check("sched: cost posture", b["cost"]["enabled"] is False)


def t_health():
    _configure_common()
    b = asyncio.run(M.health_logic())  # returns a plain dict, not JSONResponse
    check("health: status ok", b["status"] == "ok")
    check("health: version from injected app", b["version"] == "9.9.9-test")
    check("health: router block present", "enabled" in b["router"])
    check("health: dci act_count", isinstance(b["dci"]["act_count"], int))
    check("health: security allowlist sorted",
          b["security"]["allowlist_hosts"] == sorted({"localhost", "127.0.0.1"}))
    check("health: high_privilege provenance present",
          "total" in b["security"]["high_privilege_provenance"])
    check("health: passport disabled -> kid None",
          b["passport"]["enabled"] is False and b["passport"]["kid"] is None)
    check("health: passport private_key absent",
          b["passport"]["private_key_present"] is False)
    check("health: agents block lists all registry agents",
          set(b["agents"]) == {"hermes", "opencode", "disabled_peer"})
    check("health: broker_present False (nonexistent sock)",
          b["broker_present"] is False)
    check("health: db_url + port surfaced",
          b["db_url"] == "http://localhost:8000" and "port" in b)


def main():
    t_probe_one_endpoint()
    t_lane_sched_stats()
    t_kernel_managers_detail()
    t_resolve_failover_chain()
    t_cluster_health()
    t_scheduler_state()
    t_health()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

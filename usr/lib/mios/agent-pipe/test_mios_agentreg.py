#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_agentreg (R3 agent/node registry builders). Pure stdlib, no server.py/DB/pytest. Stubs the injected deps (_is_remote_endpoint, _opt_int_mb, logger, flags) via configure() and monkeypatches the module's _toml_section so the [nodes.*] reader runs offline, then asserts: _build_agent_engines folds the home/cpu/explicit bindings; _load_agent_registry parses [agents.*], inherits [agents._defaults], applies the health_gate safe-default for remote/optional kinds, indexes per-agent auth into _AGENT_AUTH_BY_HOSTPORT, and falls back to a single hermes entry when empty; _load_node_pool synthesises one node:<name> research worker per [nodes.*] entry and skips endpoint-less nodes.
# AI-related: ./mios_agentreg.py, ./mios_config.py
# AI-functions: check, t_build_agent_engines, t_load_agent_registry, t_load_node_pool, t_health_gate_via_registry, t_agent_lane, t_render_agent_catalog, t_role_system, t_dedup_pool_by_target, main
"""Unit tests for mios_agentreg (R3 strangler-fig wave)."""

import sys
import builtins

import mios_agentreg as reg

_orig_open = builtins.open

def _set_open_mock(exclude_suffixes=None, fail_all_toml=False):
    def _mocked_open(file, *args, **kwargs):
        filepath = str(file).replace("\\", "/")
        if fail_all_toml and filepath.endswith(".toml"):
            raise FileNotFoundError()
        if exclude_suffixes:
            for suffix in exclude_suffixes:
                if filepath.endswith(suffix):
                    raise FileNotFoundError()
        return _orig_open(file, *args, **kwargs)
    builtins.open = _mocked_open

def _reset_open_mock():
    builtins.open = _orig_open


_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


class _Log:
    def warning(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass


def _opt_int_mb(v):
    try:
        return int(float(v)) if v is not None and str(v).strip() != "" else 0
    except Exception:
        return 0


def _is_remote_endpoint(ep):
    ep = ep or ""
    return bool(ep) and ("localhost" not in ep) and ("127.0.0.1" not in ep)


# Inject the server-resident deps under their original names.
reg.configure(
    is_remote_endpoint=_is_remote_endpoint,
    opt_int_mb=_opt_int_mb,
    logger=_Log(),
    catalog_fail_mode="warn",
    nodes_research_only=False,
)


def t_build_agent_engines():
    # home + cpu twin come from `entry` (the built registry row); explicit
    # engines/nodes tables come from `raw_cfg` -- mirrors _load_agent_registry.
    entry = {"lane": "", "endpoint": "http://h:1/v1", "model": "m",
             "cpu_endpoint": "http://c:3/v1", "cpu_model": "cm"}
    raw = {"engines": {"GPU": {"endpoint": "http://g:2/v1/", "model": "gm"}}}
    eng = reg._build_agent_engines(raw, entry)
    check("engines: home lane defaults to gpu", "gpu" in eng, str(eng.keys()))
    check("engines: home endpoint folded", eng["gpu"]["endpoint"] == "http://g:2/v1",
          eng["gpu"]["endpoint"])  # explicit table wins + rstrip('/')
    check("engines: cpu twin folded", eng.get("cpu", {}).get("endpoint") == "http://c:3/v1")
    check("engines: explicit model", eng["gpu"]["model"] == "gm")


def t_load_agent_registry(monkeypatched_toml):
    # _load_agent_registry reads its own layered TOML files via tomllib + open();
    # we can't easily stub that, so verify the FALLBACK path (no readable TOML ->
    # single hermes default) plus the _defaults/health_gate logic through a direct
    # synthetic build is covered by t_nodes/t_defaults below. Here: fallback shape.
    import os
    _saved = os.environ.get("MIOS_TOML")
    os.environ["MIOS_TOML"] = "/nonexistent/mios-agentreg-test.toml"
    _set_open_mock(fail_all_toml=True)
    try:
        r = reg._load_agent_registry()
    finally:
        _reset_open_mock()
        if _saved is None:
            os.environ.pop("MIOS_TOML", None)
        else:
            os.environ["MIOS_TOML"] = _saved
    check("registry: empty toml -> hermes fallback", "hermes" in r, str(list(r.keys())))
    check("registry: hermes fallback default", r["hermes"].get("default") is True)


def t_load_node_pool():
    # Monkeypatch the module's _toml_section so [nodes.*] is served offline.
    _saved = reg._toml_section
    nodes = {
        "potato": {"endpoint": "http://10.0.0.9:11435/v1", "lane": "cpu",
                   "model": "mios-agent-cpu", "vram_mb": "0", "blade": "potato"},
        "inert": {"endpoint": "", "lane": "gpu"},   # skipped (no endpoint)
        "phone": {"endpoint": "http://10.0.0.5:11434/v1", "lane": "mobile",
                  "health_gate": True},
    }
    reg._toml_section = lambda section: nodes if section == "nodes" else {}
    try:
        registry = {}
        n = reg._load_node_pool(registry)
    finally:
        reg._toml_section = _saved
    check("nodes: injected count skips inert", n == 2, f"n={n}")
    check("nodes: namespaced as node:<name>",
          "node:potato" in registry and "node:phone" in registry, str(list(registry.keys())))
    check("nodes: inert (no endpoint) skipped", "node:inert" not in registry)
    pot = registry["node:potato"]
    check("nodes: canonical model default kept", pot["model"] == "mios-agent-cpu")
    check("nodes: research worker has engines map", isinstance(pot.get("engines"), dict))
    check("nodes: V4 blade field carried from [nodes.*]", pot.get("blade") == "potato",
          str(pot.get("blade")))
    check("nodes: V4 blade defaults to '' (local blade) when absent",
          registry["node:phone"].get("blade") == "", str(registry["node:phone"].get("blade")))
    check("nodes: remote node health_gated by default", pot["health_gate"] is True)
    check("nodes: research_only honours injected NODES_RESEARCH_ONLY=False",
          pot["research_only"] is False)


def t_health_gate_via_registry():
    # Drive _load_agent_registry through a real layered TOML so the _defaults
    # inheritance + health_gate safe-default + auth indexing are exercised.
    # AGY refactor (d3f2622d): _load_agent_registry now reads [agents.*] via the
    # _toml_section resolver, NOT a raw MIOS_TOML file. Feed the synthetic agents the
    # same way the other tests do -- monkeypatch reg._toml_section -- so the _defaults
    # inheritance + health_gate safe-default + per-agent auth indexing are exercised
    # offline (the old MIOS_TOML temp-file path is silently ignored by the resolver).
    agents = {
        "_defaults": {"role": "general", "strengths": ["x"]},
        "localworker": {"endpoint": "http://localhost:8643/v1", "model": "lm"},
        "remoteworker": {
            "endpoint": "http://10.1.2.3:9000/v1",
            "kind": "remote-http",
            "auth": {"header_template": "Authorization: Bearer tok123"},
        },
    }
    _saved = reg._toml_section
    reg._toml_section = lambda section: agents if section == "agents" else {}
    try:
        r = reg._load_agent_registry()
    finally:
        reg._toml_section = _saved
    check("registry: parsed both agents", "localworker" in r and "remoteworker" in r,
          str([k for k in r if k in ("localworker", "remoteworker")]))
    check("registry: _defaults inherited (role)", r["localworker"]["role"] == "general")
    check("registry: _defaults inherited (strengths)", r["localworker"]["strengths"] == ["x"])
    check("registry: local agent NOT health-gated", r["localworker"]["health_gate"] is False)
    check("registry: remote agent health-gated (safe default)",
          r["remoteworker"]["health_gate"] is True)
    check("registry: per-agent auth indexed by host:port",
          reg._AGENT_AUTH_BY_HOSTPORT.get("10.1.2.3:9000") == "Authorization: Bearer tok123",
          str(dict(reg._AGENT_AUTH_BY_HOSTPORT)))


def t_agent_lane():
    # Pure (no injected deps): explicit lane wins, else inferred from endpoint/model.
    check("lane: explicit wins", reg._agent_lane({"lane": "IGPU"}) == "igpu")
    check("lane: igpu port inferred", reg._agent_lane({"endpoint": "http://h:8450/v1"}) == "igpu")
    check("lane: igpu model inferred", reg._agent_lane({"model": "mios-igpu"}) == "igpu")
    check("lane: cpu port inferred", reg._agent_lane({"endpoint": "http://h:8458/v1"}) == "cpu")
    check("lane: cpu model inferred", reg._agent_lane({"model": "mios-agent-cpu"}) == "cpu")
    check("lane: default gpu", reg._agent_lane({"endpoint": "http://h:9999/v1"}) == "gpu")


def t_render_agent_catalog():
    # _render_agent_catalog reads _agent_lane as a module-level SIBLING (no DI).
    check("catalog: empty registry -> ''", reg._render_agent_catalog({}) == "")
    out = reg._render_agent_catalog({
        "coder": {"job": "writes code", "lane": "gpu"},
        "rsrch": {"role": "research", "strengths": ["web"], "endpoint": "http://h:8458/v1"},
    })
    check("catalog: job line present", "writes code" in out, out)
    check("catalog: explicit lane shown", "[gpu lane]" in out, out)
    check("catalog: inferred cpu lane shown", "[cpu lane]" in out, out)
    check("catalog: fallback blurb from role+strengths", "research (web)" in out, out)


def t_role_system():
    # _role_system reads the INJECTED _ROLE_SYSTEM_DIR; degrade-open to ''.
    import os
    import tempfile
    check("role: empty name -> ''", reg._role_system("") == "")
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "coder.md"), "w", encoding="utf-8") as f:
        f.write("  ROLE OVERLAY  \n")
    _saved = reg._ROLE_SYSTEM_DIR
    reg.configure(role_system_dir=d)
    try:
        check("role: reads + strips overlay", reg._role_system("coder") == "ROLE OVERLAY")
        check("role: missing file -> '' (degrade open)", reg._role_system("nope") == "")
    finally:
        if _saved is not None:
            reg.configure(role_system_dir=_saved)


def t_dedup_pool_by_target():
    # Inject the hot registry + helper deps the dedup body reads, then assert the
    # (endpoint, model) collapse, the node:* preference, the batching by-name keep,
    # and the SWARM_MAX_WIDTH cap.
    registry = {
        "a": {"endpoint": "http://h:1/v1", "model": "m"},
        "b": {"endpoint": "http://h:1/v1", "model": "m"},          # dup of a -> collapsed
        "node:n": {"endpoint": "http://h:1/v1", "model": "m"},     # same target, ranked first
        "c": {"endpoint": "http://h:2/v1", "model": "m"},          # distinct endpoint
        "sg1": {"endpoint": "http://h:3/v1", "model": "m", "api": "openai"},
        "sg2": {"endpoint": "http://h:3/v1", "model": "m", "api": "openai"},  # batching -> NOT collapsed
        "peer": {},                                                # no endpoint -> keyed by name
    }
    reg.configure(
        agent_registry=registry,
        agent_binding=lambda cfg, eng: (str(cfg.get("endpoint", "")), str(cfg.get("model", ""))),
        endpoint_key=lambda ep: str(ep).split("://")[-1].split("/")[0],
        effort_default="max",
        swarm_max_width=10,
    )
    out = reg._dedup_pool_by_target(["a", "b", "node:n", "c", "sg1", "sg2", "peer"])
    check("dedup: node:* preferred over plain dup", "node:n" in out and "a" not in out and "b" not in out, str(out))
    check("dedup: distinct endpoint kept", "c" in out)
    check("dedup: batching backend NOT collapsed", "sg1" in out and "sg2" in out, str(out))
    check("dedup: endpointless agent kept by name", "peer" in out)
    capped = reg._dedup_pool_by_target(["a", "c", "peer"])  # 3 distinct targets
    reg.configure(swarm_max_width=2)
    check("dedup: SWARM_MAX_WIDTH caps width",
          len(reg._dedup_pool_by_target(["a", "c", "peer"])) <= 2, str(capped))
    reg.configure(swarm_max_width=10)  # restore for any later test


def main():
    t_build_agent_engines()
    t_load_agent_registry(None)
    t_load_node_pool()
    t_health_gate_via_registry()
    t_agent_lane()
    t_render_agent_catalog()
    t_role_system()
    t_dedup_pool_by_target()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

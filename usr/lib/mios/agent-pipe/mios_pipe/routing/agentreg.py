# AI-hint: Agent/node REGISTRY builders extracted verbatim from server.py (refactor R3/mios_agentreg wave). Parses mios.toml [agents.*] / [nodes.*] sections (layered vendor<-/etc<-~/.config) into the {name: {endpoint,model,role,...,engines}} registry dict the dispatcher routes over: _load_agent_registry (per-agent template merge + _defaults inheritance + health_gate safe-default + per-engine binding fold + WS-FED/G2 per-agent auth indexed into _AGENT_AUTH_BY_HOSTPORT), _load_node_pool (synthesises ONE canonical research-worker node:<name> agent per [nodes.*] compute node), and _build_agent_engines (folds legacy endpoint/cpu twin + explicit engines/nodes tables into one {label:{endpoint,model}} map). server.py still owns the module-load assignment (_AGENT_REGISTRY = _load_agent_registry(); _load_node_pool(_AGENT_REGISTRY)). Pure config consts (_toml_section/BACKEND/BACKEND_MODEL/_AGENT_AUTH_BY_HOSTPORT) imported directly from mios_config; the server-resident helpers (_is_remote_endpoint, _opt_int_mb), the logger, and the CATALOG_FAIL_MODE / NODES_RESEARCH_ONLY flags are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./mios_config.py, ./server.py, ./test_mios_agentreg.py, /usr/share/mios/mios.toml
# AI-functions: _build_agent_engines, _load_agent_registry, _load_node_pool, _agent_lane, _render_agent_catalog, _role_system, _dedup_pool_by_target, configure
"""mios_agentreg -- agent/node registry builders (R3 strangler-fig extraction).

Verbatim move of the mios.toml [agents.*] / [nodes.*] registry parsers out of the
server.py monolith. Pure config readers + constants come straight from
mios_config; the few server.py runtime symbols these parsers touch
(_is_remote_endpoint, _opt_int_mb, the logger, CATALOG_FAIL_MODE,
NODES_RESEARCH_ONLY) are injected once via :func:`configure` AFTER they are
defined in server.py. server.py keeps the module-load assignment of the result to
_AGENT_REGISTRY and the node-pool injection -- these functions only BUILD the
dict, they never own it.
"""

from __future__ import annotations

import os

import mios_hopbudget   # WS-4 effort-width width cap (pure module; never imports server)

# Pure config SSOT -- genuinely owned by mios_config (mutable _AGENT_AUTH_BY_
# HOSTPORT is the SAME object server.py imports, so mutating it here is shared).
from mios_config import (  # noqa: E402
    _toml_section,
    BACKEND,
    BACKEND_MODEL,
    _AGENT_AUTH_BY_HOSTPORT,
)

# -- Dependency-injected server.py symbols (set by configure(); kept under their
# ORIGINAL server names so the moved bodies are byte-identical). Placeholders so
# a bare ``import mios_agentreg`` still succeeds before configure() runs.
_is_remote_endpoint = None
_opt_int_mb = None
log = None
CATALOG_FAIL_MODE = "warn"
NODES_RESEARCH_ONLY = False

# -- Additional injected deps for the agent-registry HELPERS moved alongside the
# builders (_dedup_pool_by_target / _render_agent_catalog / _role_system). Kept under
# their ORIGINAL server names so the moved bodies stay byte-identical. _AGENT_REGISTRY
# is the SAME hot dict server.py owns: injected by reference and RE-injected on a live
# membership reload (server reassigns it there). _agent_binding / _endpoint_key are
# server-resident helpers; EFFORT_DEFAULT / SWARM_MAX_WIDTH / _ROLE_SYSTEM_DIR are
# server-owned config scalars (in the importable surface) injected by value. Placeholders
# so a bare ``import mios_agentreg`` still succeeds before configure() runs.
_AGENT_REGISTRY: dict = {}
_agent_binding = None
_endpoint_key = None
_ROLE_SYSTEM_DIR = None
EFFORT_DEFAULT = None
SWARM_MAX_WIDTH = None


def configure(*, is_remote_endpoint=None, opt_int_mb=None, logger=None,
              catalog_fail_mode=None, nodes_research_only=None,
              agent_registry=None, agent_binding=None, endpoint_key=None,
              role_system_dir=None, effort_default=None, swarm_max_width=None) -> None:
    """Inject the server.py runtime helpers/flags the registry builders + helpers read.

    Called from server.py possibly MORE THAN ONCE with a partial set: the builders'
    deps are injected as soon as they are defined, while the helpers' deps (the hot
    _AGENT_REGISTRY, _agent_binding / _endpoint_key, the EFFORT_DEFAULT / SWARM_MAX_WIDTH
    scalars and _ROLE_SYSTEM_DIR) are injected later -- once defined -- and _AGENT_REGISTRY
    is re-injected on a live membership reload (it is reassigned there). Each field gates
    on ``is not None`` so a partial call never clobbers an already-injected dep."""
    global _is_remote_endpoint, _opt_int_mb, log
    global CATALOG_FAIL_MODE, NODES_RESEARCH_ONLY
    global _AGENT_REGISTRY, _agent_binding, _endpoint_key
    global _ROLE_SYSTEM_DIR, EFFORT_DEFAULT, SWARM_MAX_WIDTH
    if is_remote_endpoint is not None:
        _is_remote_endpoint = is_remote_endpoint
    if opt_int_mb is not None:
        _opt_int_mb = opt_int_mb
    if logger is not None:
        log = logger
    if catalog_fail_mode is not None:
        CATALOG_FAIL_MODE = catalog_fail_mode
    if nodes_research_only is not None:
        NODES_RESEARCH_ONLY = nodes_research_only
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if agent_binding is not None:
        _agent_binding = agent_binding
    if endpoint_key is not None:
        _endpoint_key = endpoint_key
    if role_system_dir is not None:
        _ROLE_SYSTEM_DIR = role_system_dir
    if effort_default is not None:
        EFFORT_DEFAULT = effort_default
    if swarm_max_width is not None:
        SWARM_MAX_WIDTH = swarm_max_width


def _build_agent_engines(raw_cfg: dict, entry: dict) -> dict:
    """Fold an agent's bindings into an {engine: {endpoint, model}} map.
    Precedence (low -> high): the primary endpoint/model as the agent's HOME
    engine (its lane, or 'gpu'); the legacy cpu_endpoint/cpu_model as
    engines['cpu']; explicit [agents.<name>.engines.<engine>] tables WIN. So
    legacy 2-lane configs keep working unchanged AND any agent can declare a
    binding on any engine. iGPU stays DISTINCT from cpu here (the operator lists
    it as its own engine), though _agent_lane still collapses them for fan-out
    diversity."""
    engines: dict = {}
    home = (str(entry.get("lane") or "").strip() or "gpu")
    if entry.get("endpoint"):
        engines[home] = {"endpoint": entry["endpoint"],
                         "model": entry.get("model", "")}
    if entry.get("cpu_endpoint"):
        engines["cpu"] = {"endpoint": entry["cpu_endpoint"],
                          "model": entry.get("cpu_model") or entry.get("model", "")}
    # Explicit per-binding tables WIN. BOTH [agents.<name>.engines.<label>] AND
    # [agents.<name>.nodes.<label>] are read into the same map: an ENGINE
    # (cpu/gpu/igpu/accelerator) and a NODE (iPhone/Android/another MiOS host or
    # cluster, by its tailnet endpoint) are both just an endpoint+model the agent
    # can run on ("any Agent/Sub-Agent can run on any
    # node/endpoint"). The label is free-form; the endpoint decides reachability.
    for _tbl in ("engines", "nodes"):
        raw = raw_cfg.get(_tbl)
        if isinstance(raw, dict):
            for label, b in raw.items():
                if isinstance(b, dict) and b.get("endpoint"):
                    engines[str(label).lower().strip()] = {
                        "endpoint": str(b["endpoint"]).rstrip("/"),
                        "model": str(b.get("model") or entry.get("model", "")),
                    }
    return engines


def _load_agent_registry() -> dict[str, dict]:
    """Parse mios.toml [agents.*] sections into a registry dict.
    Returns {name: {endpoint, model, role, default, strengths}}.
    Read at module load + cached -- operator restarts agent-pipe
    to pick up changes (same pattern as ports/security/...).

    Fallback: when the TOML can't be read or has no [agents.*],
    returns a single hermes entry pointing at MIOS_AGENT_PIPE_
    BACKEND so the legacy path still works."""
    registry: dict[str, dict] = {}
    # LAYERED overlay (operator overlay wins): vendor <- /etc <- ~/.config.
    # A host can set a PRIVATE / per-host agent field -- e.g. the ai-local
    # phone's tailnet `endpoint` -- in /etc/mios/mios.toml WITHOUT baking it
    # into the PUBLIC vendor mios.toml (which ships it empty for privacy).
    # Each [agents.<name>] is merged field-by-field, so an overlay can set just
    # `endpoint` and inherit the rest. Mirrors the firstboot toml-layer reader.
    _base = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    _layers = [_base, "/etc/mios/mios.toml",
               os.path.expanduser("~/.config/mios/mios.toml")]
    try:
        try:
            import tomllib  # py311+
        except ImportError:
            import tomli as tomllib  # fallback (Fedora <= py310)
        agents: dict = {}
        for _p in _layers:
            try:
                with open(_p, "rb") as _f:
                    _d = tomllib.load(_f)
            except (OSError, tomllib.TOMLDecodeError):
                continue
            for _n, _cfg in (_d.get("agents") or {}).items():
                if isinstance(_cfg, dict):
                    agents.setdefault(_n, {}).update(_cfg)
        # Unified agent template (roadmap WS-A1): every [agents.<name>] inherits
        # [agents._defaults], overriding only what differs -- ONE merge path so an
        # agent can never silently miss a safety field (the opencode merged_chars=0
        # bug = opencode lacked health_gate while the hermes-worker had it). Reserved
        # `_`-prefixed names are skipped as non-agents. Absent _defaults => {} =>
        # byte-identical to the prior behaviour.
        _agent_defaults = (agents.pop("_defaults", {})
                           if isinstance(agents.get("_defaults"), dict) else {})
        _AGENT_AUTH_BY_HOSTPORT.clear()  # WS-FED/G2: rebuilt each load
        for name, cfg in agents.items():
            if name.startswith("_") or not isinstance(cfg, dict):
                continue
            cfg = {**_agent_defaults, **cfg}
            # SAFE health_gate default: a LOCAL-but-OPTIONAL endpoint (a default-off
            # unit, or kind in cli/remote/edge/node/a2a) MUST be liveness-probed --
            # otherwise _should_health_probe never probes a dead LOCAL endpoint,
            # _live_agent_names marks it live, and _reroute_dead_nodes sinks DAG
            # facets onto it -> merged_chars=0. Mirrors the node-loader's safe default.
            _ep_x = os.path.expandvars(str(cfg.get("endpoint", ""))).rstrip("/")
            _kind = str(cfg.get("kind", "")).strip().lower()
            _hg_default = (
                _kind in ("remote-http", "cli", "mobile", "edge", "node", "a2a")
                or not bool(cfg.get("enabled", True))
                or _is_remote_endpoint(_ep_x)
            )
            registry[name] = {
                # expandvars: [agents.*].endpoint is stored as a deferred
                # ${MIOS_PORT_*} template (e.g. the :8643 hermes-worker); the
                # env supplies the numeric port (install.env). Without this the
                # registry kept a literal "${MIOS_PORT_HERMES_WORKER}" -> httpx
                # InvalidURL -> :8640 500 on every request. install-robustness.
                "endpoint": os.path.expandvars(str(cfg.get("endpoint", ""))).rstrip("/"),
                "model":    str(cfg.get("model", name)),
                "role":     str(cfg.get("role", "general")),
                "default":  bool(cfg.get("default", False)),
                "strengths": list(cfg.get("strengths") or []),
                "lane":     str(cfg.get("lane", "")).lower().strip(),
                # WS-2 per-agent RBAC: optional verb allow/deny for THIS agent's
                # tool surface (default empty = no restriction). Consumed by
                # _agent_rbac_filter at dispatch.
                "denied_verbs":  list(cfg.get("denied_verbs") or []),
                "allowed_verbs": list(cfg.get("allowed_verbs") or []),
                # #55 per-tool capability/risk gate: optional ceiling on the
                # permission tier (read|write|interactive) this agent may call.
                # Empty = no ceiling (default => zero behaviour change). Also
                # consumed by _agent_rbac_filter; verbs whose permission tier
                # exceeds this rank are dropped from the agent's surface.
                "max_permission": str(cfg.get("max_permission", "")).strip().lower(),
                # fan-out opt-out (default True = eligible as a secondary).
                "fanout":   bool(cfg.get("fanout", True)),
                # CPU-compute twin (every agent has a
                # Modelfile for both CPU + GPU). When this agent runs as a
                # concurrent fan-out SECONDARY, _call_agent_complete prefers
                # this lane/model so the secondary offloads to the CPU lane
                # and the dGPU stays free for the primary. Empty = single-lane.
                "cpu_endpoint": str(cfg.get("cpu_endpoint", "")).rstrip("/"),
                "cpu_model":    str(cfg.get("cpu_model", "")),
                # health_gate ("client endpoints join the
                # swarm when they join"): a client-hosted node (e.g. a phone
                # running a local model over Tailscale) that comes and goes.
                # When set, the secondary call uses a SHORT timeout so a
                # sleeping/absent node drops from the merge fast instead of
                # stalling the turn -- auto-join-when-up, auto-drop-when-gone.
                "health_gate":  bool(cfg.get("health_gate", _hg_default)),
                # P3.2 cluster resilience ("remove
                # :8642/:11434 SPOFs"): ordered list of agent names to fall back
                # to when this agent's PRIMARY endpoint is dead. The router
                # picks the first live name in this chain (then this agent's
                # own cpu_endpoint as a final fallback, then a hard error).
                # Mios.toml shape: failover_agents = ["name1", "name2"]
                "failover_agents": [str(s) for s in (cfg.get("failover_agents")
                                                    or []) if str(s).strip()],
                # research_only ("research should dispatch
                # as many 2-4GB models as possible across all lanes"): a
                # lightweight RESEARCH-WORKER agent EXCLUDED from the normal
                # council/swarm pool (everyday turns stay light), joining ONLY
                # RESEARCH / deep-research turns. The [nodes.*] pool
                # (_load_node_pool) is the canonical way to spread the worker
                # brain across compute nodes; this per-agent flag carries the
                # same research-turn-only membership for a hand-declared
                # [agents.*] entry.
                "research_only": bool(cfg.get("research_only", False)),
                # WS-A1 unified-template fields (kind discriminator + the cli/
                # optional contract the schema validator enforces in 38-drift-checks).
                "kind":      (_kind or ("remote-http" if _is_remote_endpoint(_ep_x)
                                        else "local-http")),
                "enabled":   bool(cfg.get("enabled", True)),
                "transport": str(cfg.get("transport",
                                         "cli" if _kind == "cli" else "http")).strip().lower(),
                "timeout_s": int(cfg.get("timeout_s", 0) or 0),
                # WS-FED/G2: per-agent credential + trust posture.
                "auth":  cfg.get("auth") if isinstance(cfg.get("auth"), dict) else {},
                "trust": cfg.get("trust") if isinstance(cfg.get("trust"), dict) else {},
            }
            # Per-engine + per-node binding map ("any Agent
            # in any AI engine -- CPU/dGPU/iGPU/accelerator" + "any Agent/Sub-
            # Agent on any node/endpoint -- iPhone/Android/other MiOS nodes").
            # Folds the legacy endpoint/model + cpu twin AND any explicit
            # [agents.<name>.engines.*] / [agents.<name>.nodes.*] tables into one
            # {label: {endpoint, model}} map -- backward-compatible.
            registry[name]["engines"] = _build_agent_engines(cfg, registry[name])
            # WS-FED/G2: index this agent's resolved credential by endpoint
            # host:port so dispatch attaches it to a non-backend (remote) endpoint.
            # Only a fully env-resolved "Header: value" is stored (degrade-open).
            _auth_t = str((registry[name].get("auth") or {}).get("header_template") or "").strip()
            _ep0 = registry[name].get("endpoint") or ""
            if _auth_t and _ep0:
                _hp0 = _ep0.split("://")[-1].split("/")[0]
                _rendered = os.path.expandvars(_auth_t)
                if _hp0 and "${" not in _rendered and ":" in _rendered:
                    _AGENT_AUTH_BY_HOSTPORT[_hp0] = _rendered
    except Exception as e:
        log.warning("agent registry load failed: %s; using fallback", e)
        if CATALOG_FAIL_MODE == "fail":   # WS-A1 fail-loud (opt-in)
            raise
    if not registry:
        registry["hermes"] = {
            "endpoint": BACKEND, "model": BACKEND_MODEL,
            "role": "general", "default": True, "strengths": [],
        }
    return registry


def _load_node_pool(registry: dict[str, dict]) -> int:
    """Synthesise ONE canonical research-worker agent PER compute NODE from the
 mios.toml [nodes.*] table -- "don't have separate CPU
    1,2,3 / dGPU 1,2,3 replicas -- there should just be a MiOS Modelfile dispatched
    as many times as needed to ANY node(s)".

    ONE canonical brain x N nodes -- not N hand-partitioned per-lane research
    workers, and never a raw base model (a raw base cold-loaded on a CPU-only lane
    was the loadavg runaway). Each [nodes.<name>] declares an endpoint + a CANONICAL
    Modelfile tag (mios-agent on GPU, mios-agent-cpu on CPU/light, mios-igpu) +
    lane; we inject `node:<name>` into the registry with research_only defaulting to
    the SSOT NODES_RESEARCH_ONLY and fanout=true, so
    the EXISTING capacity-aware fan-out / swarm-DAG logic (_pick_fanout_agents /
    _agent_dag_from_tasks, bounded by the P1 admission controller + per-lane / per-
    endpoint semaphores) dispatches the ONE worker brain across the pool by
    capacity. Mirrors the a2a:<pid> synthetic-agent injection.

    Layered read (vendor <- /etc <- ~/.config) via _toml_section so the operator
    overlay adds real REMOTE node endpoints (potato/phone/cluster) without baking
    tailnet IPs into the public vendor file. Degrade-open: no [nodes.*] -> 0 nodes
    injected, registry unchanged. Returns the count injected.

    Per-node fields (all but endpoint optional):
      endpoint    -- OpenAI /v1 (or ollama) URL; EMPTY = inert node, skipped.
      model       -- canonical Modelfile tag the node serves (default mios-agent).
      lane        -- gpu/cpu/igpu/mobile/... (semaphore + fan-out diversity bucket).
      health_gate -- true for a come-and-go remote node (auto-join/drop); local
                     nodes omit it (always live). Defaults true for non-local lanes.
      fanout      -- fan-out opt-out (default true).
      role/job/strengths -- optional metadata; sensible worker defaults applied.
    The light-lane model is additionally force-capped to the micro model at
    dispatch by _cap_cpu_lane_model (belt + suspenders)."""
    try:
        nodes = _toml_section("nodes")
    except Exception as e:  # noqa: BLE001 -- degrade-open
        log.warning("node pool load failed: %s; no nodes injected", e)
        return 0
    if not isinstance(nodes, dict) or not nodes:
        return 0
    n = 0
    for name, cfg in nodes.items():
        if not isinstance(cfg, dict):
            continue
        ep = str(cfg.get("endpoint", "")).rstrip("/")
        if not ep:
            continue  # inert / privacy-empty node (e.g. vendor local-igpu)
        lane = str(cfg.get("lane", "")).lower().strip() or "gpu"
        # A LOCAL lane is always-live; a REMOTE node comes and goes, so it is
        # health-gated by default (auto-join when reachable / drop when gone),
        # unless the node explicitly overrides. localhost/127.0.0.1 == local.
        _is_local = ("localhost" in ep) or ("127.0.0.1" in ep)
        health_gate = bool(cfg.get("health_gate", not _is_local))
        entry: dict = {
            "endpoint": ep,
            # The node serves a CANONICAL Modelfile tag, never a raw base.
            "model":    str(cfg.get("model") or "mios-agent"),
            "role":     str(cfg.get("role", "research")),
            "job":      str(cfg.get("job",
                          "Concurrent research worker -- one MiOS-Agent brain "
                          "dispatched on this node to research a facet in "
                          "parallel with the rest of the pool.")),
            "default":  False,
            "strengths": list(cfg.get("strengths")
                              or ["research", "web_search", "summarize"]),
            "lane":     lane,
            # V4 blade (machine) topology: which PHYSICAL MACHINE this compute node
            # lives on -- so "nodes X, Y, Z are one machine" is EXPRESSIBLE and the
            # per-blade admission (V5) can compare a node's residents against ITS
            # blade's VRAM budget, not the single LOCAL scalar. Free-form, matching a
            # [blades.<name>] key; EMPTY -> the local blade (server resolves the local
            # name from the [identity] hostname SSOT), so a config with no blade
            # fields keeps every node on the local blade = byte-identical to today.
            "blade":     str(cfg.get("blade", "")).strip(),
            # SWARM Phase-0/1 : sub_lane = per-engine
            # semaphore key (e.g. 'gpu0') so N single-model servers on ONE device
            # each get independent concurrency; vram_mb/ram_mb = this worker's
            # resident cost feeding per-endpoint admission so the dispatcher packs
            # by REAL headroom (never OOM-cascades the 4090); tool_capable
            # (default true) = the worker gets the global tool surface. All
            # optional SSOT fields -> absent today = byte-identical behaviour.
            "sub_lane":  str(cfg.get("sub_lane", "")).lower().strip(),
            "vram_mb":   _opt_int_mb(cfg.get("vram_mb")),
            "ram_mb":    _opt_int_mb(cfg.get("ram_mb")),
            "tool_capable": bool(cfg.get("tool_capable", True)),
            "fanout":   bool(cfg.get("fanout", True)),
            "cpu_endpoint": str(cfg.get("cpu_endpoint", "")).rstrip("/"),
            "cpu_model":    str(cfg.get("cpu_model", "")),
            # Node-declared protocol (operator no-hardcode): 'llamacpp'/'vulkan'
            # -> /slots KV-paging + no forced tool_choice; 'openai'/'ollama' as
            # usual. Carried so _binding_api/_endpoint_is_llamacpp honour it
            # WITHOUT relying on a port substring (e.g. an iGPU llama.cpp node).
            "api":          str(cfg.get("api", "")).strip().lower(),
            "health_gate":  health_gate,
            "failover_agents": [str(s) for s in (cfg.get("failover_agents")
                                                or []) if str(s).strip()],
            # research_only membership for the node pool: when set, a node is
            # excluded from everyday council/chat turns (keeps them light) and
            # joins ONLY research/deep turns -- ONE canonical brain x N nodes
            # carrying that research-turn-only behaviour without N bespoke entries.
            # DEFAULT is the SSOT NODES_RESEARCH_ONLY ("all
            # nodes enabled by default"): False -> every node joins EVERY turn
            # (kept safe by admission + COUNCIL_MAX + per-endpoint/lane semaphores
            # + lane priority), per-node override still wins.
            "research_only": bool(cfg.get("research_only", NODES_RESEARCH_ONLY)),
        }
        entry["engines"] = _build_agent_engines(cfg, entry)
        # node:<name> namespacing keeps these distinct from [agents.*] (and from
        # a2a:<pid>) so a node can't collide with / clobber a real sub-agent.
        registry[f"node:{name}"] = entry
        n += 1
    if n:
        log.info("node pool: injected %d research-worker node(s) "
                 "(ONE canonical MiOS Modelfile dispatched per node)", n)
    return n


# ── Agent-registry rendering / lane / pool-dedup HELPERS (strangler-fig refactor) ──
# Moved VERBATIM from server.py. _agent_lane is pure (no deps); _render_agent_catalog
# reads it as a module-level SIBLING (so the server's import-time render call needs no
# injection); _role_system reads the injected _ROLE_SYSTEM_DIR; _dedup_pool_by_target
# reads the injected hot _AGENT_REGISTRY + _agent_binding / _endpoint_key + the
# EFFORT_DEFAULT / SWARM_MAX_WIDTH scalars (mios_hopbudget is imported directly above).
# server.py re-imports each under its EXACT original name so the surface is byte-identical.


def _agent_lane(cfg: dict) -> str:
    """Resolve an agent's COMPUTE LANE -- the distinct hardware it runs on:
    'gpu' (the dGPU/4090), 'cpu' (the in-VM CPU), 'igpu' (an iGPU, e.g. the
    Windows llama.cpp node :11436), 'accelerator', or 'mobile' (a client node).
    DISTINCT lanes do NOT contend, so the council fires one agent PER LANE
 CONCURRENTLY and each gets its own _lane_sem ("iGPU
    fires WITH CPU cores as well as the rest of the engines/hardware/nodes").
    Explicit [agents.*].lane wins; else infer from endpoint/model. iGPU is now
    its OWN lane (was collapsed into 'cpu', which queued it behind CPU work)."""
    lane = str(cfg.get("lane", "")).lower().strip()
    if lane in ("cpu", "gpu", "igpu", "accelerator", "mobile"):
        return lane
    ep = str(cfg.get("endpoint", ""))
    mdl = str(cfg.get("model", "")).lower()
    _light_port = os.environ.get("MIOS_PORT_LLM_LIGHT", "8450")
    _cpu_port = os.environ.get("MIOS_PORT_CPU_NODE", "8458")
    if (":" + _light_port) in ep or "igpu" in mdl:        # iGPU / light lane
        return "igpu"
    if ":8644" in ep or (":" + _cpu_port) in ep or "cpu" in mdl:
        return "cpu"
    return "gpu"


def _render_agent_catalog(registry: dict) -> str:
    """Render the sub-agent roster for the planner as JOBS, not fixed roles
 ("no fixed roles -- MiOS-Agents are modelfiles for
    jobs and tools/skills/recipes"). Each agent is described by its `job`
    (mios.toml [agents.<name>].job, SSOT) -- what its Modelfile is BEST at --
    falling back to a blurb derived from role + strengths tags when no job is
    set. Every agent has GLOBAL access to all MiOS verbs/recipes/skills, so the
    planner routes purely by CAPABILITY + compute LANE (to spread work across
    CPU/GPU/iGPU concurrently), never by tool availability. Pulled from
    _AGENT_REGISTRY (mios.toml [agents.*] SSOT)."""
    if not registry:
        return ""
    lines = [
        "  -- sub-agents (delegate a sub-task via an `agent` node) --",
        "  every agent wields ALL MiOS tools/recipes/skills; pick by the JOB it",
        "  is best at + its compute lane (spread work across lanes), NOT by tools:",
    ]
    for name, cfg in sorted(registry.items()):
        lane = _agent_lane(cfg)
        job = str(cfg.get("job") or "").strip()
        if not job:
            # Fallback: derive a capability blurb from role + strengths tags so
            # an agent without an explicit `job` still routes sensibly.
            role = str(cfg.get("role", "general"))
            strengths = ", ".join(str(s) for s in (cfg.get("strengths") or []))
            job = role + (f" ({strengths})" if strengths else "")
        lines.append(f"  {name}".ljust(24) + f"[{lane} lane] -- {job}")
    return "\n".join(lines)


def _role_system(aname: str) -> str:
    """Per-role DEVELOPER overlay (OpenAI developer-message pattern), layered
    AFTER the /MiOS.md SYSTEM identity. Generated by mios-gen-role-system from the
    SSOT (thin: role + tool-focus pointer + live fleet, ~340 B). Degrade-open to ''
 so a missing/unreadable overlay never breaks dispatch.."""
    if not aname:
        return ""
    try:
        with open(os.path.join(_ROLE_SYSTEM_DIR, f"{aname}.md"),
                  "r", encoding="utf-8") as _f:
            return _f.read().strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _dedup_pool_by_target(pool: list) -> list:
    """Collapse a fan-out pool to DISTINCT (endpoint, model) targets + cap width
 ("all these hardcoded agents" / 16-agent explosion). Several
    pool members -- node-pool synthetics and/or research_only agents -- can resolve
    to the SAME endpoint+model -> N IDENTICAL dispatches = pure redundancy + idle
    thrash. Keep ONE agent per (endpoint, model) so the swarm fans across DISTINCT
    compute targets, not duplicates (model diversity on one endpoint is preserved --
    a different model => a different key). PREFER a node:* synthetic, then a
    first-class agent, over a plain research_only agent for the same target. Then cap to SWARM_MAX_WIDTH.
    Agents with no resolvable endpoint (a2a peers, bespoke gateways) are keyed by
    name so they're never collapsed."""
    def _rank(a: str) -> int:
        if str(a).startswith("node:"):
            return 0
        return 2 if (_AGENT_REGISTRY.get(a) or {}).get("research_only") else 1
    seen: set = set()
    keep: set = set()
    for a in sorted(pool, key=lambda x: (_rank(x), str(x))):
        c = _AGENT_REGISTRY.get(a) or {}
        try:
            _ep, _mdl = _agent_binding(c, None)
        except Exception:  # noqa: BLE001
            _ep, _mdl = str(c.get("endpoint", "")), str(c.get("model", ""))
        # A CONTINUOUS-BATCHING backend (SGLang / vLLM, api=openai) serves
        # concurrent requests IN PARALLEL -- so do NOT collapse multiple nodes
        # that target it ("ALL AGENTS USE SGLANG": the
        # concurrent swarm fans N research facets onto the one batching server).
        # Key such nodes by NAME so each stays a distinct fan-out target; the
        # SWARM_MAX_WIDTH cap below still bounds total concurrency. Only
        # SERIALIZING backends (llama.cpp/ollama -- one model loaded at a time,
        # which THRASHED when 4 nodes requested different models) keep the
        # (endpoint, model) collapse that prevents redundant identical dispatch.
        _batching = str(c.get("api", "")).strip().lower() in {"openai", "sglang", "vllm"}
        if _ep and _batching:
            key = ("@name:" + str(a), "")
        elif _ep:
            key = (_endpoint_key(_ep), str(_mdl or ""))
        else:
            key = ("@" + str(a), "")
        if key in seen:
            continue
        seen.add(key)
        keep.add(a)
    out = [a for a in pool if a in keep]   # restore natural order (primary first)
    # WS-4: cap to the EFFORT-scaled width (1..SWARM_MAX_WIDTH). Default effort
    # "max" -> the full SWARM_MAX_WIDTH (unchanged); a lower effort narrows the
    # fan-out so orchestration intensity tracks query complexity.
    _eff_w = (mios_hopbudget.effort_width(EFFORT_DEFAULT, base=2, cap=SWARM_MAX_WIDTH)
              if SWARM_MAX_WIDTH > 0 else 0)
    if _eff_w > 0 and len(out) > _eff_w:
        out = out[:_eff_w]
    return out

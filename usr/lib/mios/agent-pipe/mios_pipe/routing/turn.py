# AI-hint: PER-TURN message-prep + agent-selection helpers extracted VERBATIM from
#   server.py (strangler-fig refactor). _extract_last_user_text pulls the latest user
#   text out of an OpenAI messages[] (string or multimodal-parts content). _pick_agent
#   selects a sub-agent by role (exact-role -> default -> first) and degrade-opens a
#   gated/unreachable health_gate node back onto the local lane. _casual_agent_label maps
#   a registered agent name -> a generic surface label (role-agent / sub-agent) so the
#   specific daemon name never leaks to the chat UI. _live_agent_names is the per-turn
#   LIVE roster -- non-health_gate lanes are always live, health_gate client/Tailscale
#   nodes are connect-probed + TTL-cached in _NODE_LIVE so an outage prunes the node
#   without re-probing every turn. _split_think_tags / _strip_think_tags lift the
#   <think>-family reasoning out of model output (captured for a dropdown, stripped from
#   the answer). Every server-side dep (the live agent registry + node-liveness cache,
#   the health-probe + probe-auth helpers, the liveness TTL/connect scalars, and the
#   think-tag regexes) is dependency-INJECTED via configure() (one-way boundary -- this
#   module NEVER imports server). server.py re-imports the names under their exact
#   aliases so the importable surface stays byte-identical.
# AI-related: ./server.py, ./mios_config.py, ./test_mios_turn.py
# AI-functions: _extract_last_user_text, _pick_agent, _casual_agent_label, _live_agent_names, _split_think_tags, _strip_think_tags, configure
"""PER-TURN message-prep + agent-selection helpers (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. These are the small cohesive turn-prep
helpers the chat router + responders call each turn: last-user-text extraction,
role-based sub-agent selection (with degrade-open on a dead gated node), the
generic agent surface label, the per-turn live-agent roster (health-probed +
TTL-cached), and the <think>-tag reasoning/answer split. Every server-resident
symbol -- the live agent registry, the node-liveness cache, the health-probe +
probe-auth helpers, the liveness TTL/connect scalars, and the think-tag regexes
-- is injected via :func:`configure` (one-way boundary -- this module never
imports ``server``). ``server.py`` re-imports each name under its original alias
so the importable surface stays byte-identical.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx


# -- Dependency-injection seam ----------------------------------------
# server.py calls configure() with these AFTER every one is defined (one-way
# boundary: this module never imports server). _AGENT_REGISTRY is REBOUND on a
# live membership reload, so server re-injects it from _reload_membership; the
# rest are stable bindings (mutable-by-reference for _NODE_LIVE). The placeholders
# below let a standalone import succeed; every consumer runs after configure().
_AGENT_REGISTRY = None
_NODE_LIVE = None
_should_health_probe = None
_probe_auth_headers = None
NODE_LIVENESS_TTL_S = 45.0
NODE_LIVENESS_CONNECT_S = 6.0
_THINK_OPENERS = ()
_THINK_CAP_RE = None
_THINK_CAP_UNCLOSED_RE = None
_THINK_ORPHAN_RE = None


_INJECTED = frozenset((
    "_AGENT_REGISTRY", "_NODE_LIVE", "_should_health_probe", "_probe_auth_headers",
    "NODE_LIVENESS_TTL_S", "NODE_LIVENESS_CONNECT_S", "_THINK_OPENERS", "_THINK_CAP_RE",
    "_THINK_CAP_UNCLOSED_RE", "_THINK_ORPHAN_RE",
))


def configure(**deps) -> None:
    """Inject server-side deps under their EXACT original names (one-way boundary).

    Called from ``server.py`` after every injected symbol is defined, and again
    from ``_reload_membership`` to re-bind ``_AGENT_REGISTRY`` after a live add/drop.
    Each keyword equals the module global it sets.
    """
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


async def _live_agent_names() -> set:
    """Set of agent names currently USABLE for dispatch (
    "iGPU is down"). Non-health_gate agents are ALWAYS live -- they are local
    lanes whose failure is a separate, louder problem and probing them every
    turn only adds latency. Only health_gate client/Tailscale nodes (the iGPU,
    a phone) -- the ones that legitimately come and go -- are connect-probed,
    TTL-cached in _NODE_LIVE so an OUTAGE drops the node from the swarm roster
    WITHOUT re-probing every turn (it rejoins within the TTL once back up).
    Used to prune dead nodes before the planner/DAG assigns them a facet, so the
    freed concurrent lane re-routes to live compute instead of vanishing."""
    live: set = set()
    to_probe: list = []
    now = time.time()
    for name, cfg in _AGENT_REGISTRY.items():
        if not _should_health_probe(cfg):
            live.add(name)
            continue
        cached = _NODE_LIVE.get(name)
        if cached and (now - cached[0]) < NODE_LIVENESS_TTL_S:
            if cached[1]:
                live.add(name)
        else:
            to_probe.append((name, cfg))
    if to_probe:
        _to = httpx.Timeout(connect=NODE_LIVENESS_CONNECT_S,
                            read=NODE_LIVENESS_CONNECT_S, write=2.0, pool=2.0)

        async def _probe1(client, ep: str) -> bool:
            ep = (ep or "").rstrip("/")
            if not ep:
                return False
            try:  # OpenAI /v1/models first (llama.cpp + vLLM speak this)
                r = await client.get(f"{ep}/models", headers=_probe_auth_headers(ep))
                if r.status_code < 500:
                    return True
            except Exception:
                pass
            tb = ep[:-3].rstrip("/") if ep.endswith("/v1") else ep
            try:  # ollama-style /api/tags fallback
                r = await client.get(f"{tb}/api/tags")
                return r.status_code < 500
            except Exception:
                return False

        try:
            async with httpx.AsyncClient(verify=False, timeout=_to,
                                         follow_redirects=False) as client:
                results = await asyncio.gather(
                    *[_probe1(client, c.get("endpoint")) for _n, c in to_probe],
                    return_exceptions=True)
        except Exception:  # noqa: BLE001 -- probe is best-effort; degrade open
            results = [False] * len(to_probe)
        for (name, _cfg), ok in zip(to_probe, results):
            ok = bool(ok) and not isinstance(ok, Exception)
            _NODE_LIVE[name] = (time.time(), ok)
            if ok:
                live.add(name)
    return live


def _pick_agent(role: str) -> tuple[str, dict]:
    """Pick a sub-agent by role match. Order: exact-role -> default
    -> first registered. Returns (name, cfg).

 Degrade-open (install-robustness): if the chosen agent is a
    health_gate (come-and-go) node -- e.g. the :8643 hermes-worker bound to the
    heavy GPU lane, which is gated off by default -- that the liveness cache does
    NOT confirm reachable, blank its endpoint so the caller's `endpoint or
    BACKEND` falls back to the always-on local lane. Without this the PRIMARY
    dispatch went to a dead gated worker -> httpx "All connection attempts
    failed" -> 502 on EVERY turn on any host where that lane is down (a fresh
    dev VM, a CPU host). The worker is still used the moment the probe confirms
    it live (heavy lane enabled)."""
    role = (role or "").lower().strip()
    chosen = None
    if role:
        for name, cfg in _AGENT_REGISTRY.items():
            if cfg.get("role", "").lower() == role:
                chosen = (name, cfg)
                break
    if chosen is None:
        for name, cfg in _AGENT_REGISTRY.items():
            if cfg.get("default"):
                chosen = (name, cfg)
                break
    if chosen is None:
        _n = next(iter(_AGENT_REGISTRY))
        chosen = (_n, _AGENT_REGISTRY[_n])
    name, cfg = chosen
    if cfg.get("health_gate"):
        _c = _NODE_LIVE.get(name)
        if not (_c and _c[1]):  # not confirmed reachable -> fall back to BACKEND
            # Blank the endpoint AND swap the model: this agent's model (e.g.
            # the worker's heavy "mios-heavy") is NOT served by BACKEND (the
            # light llama-swap lane), so keeping it yields llama-swap "no router
            # for requested model". Reset to MIOS_AI_MODEL (the light-lane
            # default) so the fallback request routes. install-robustness.
            _fb_model = (os.environ.get("MIOS_AI_MODEL") or "").strip()
            cfg = {**cfg, "endpoint": "", **({"model": _fb_model} if _fb_model else {})}
    return name, cfg


def _split_think_tags(text: str) -> tuple[str, str]:
    """Split model output into (reasoning, answer).

 'there SHOULD be thinking -- as a dropdown' AND
    'thinking bleeding into the final response makes it look like it
    answered twice'. The fix is to CAPTURE the <think>-family reasoning
    (so it can go in a collapsed dropdown) instead of discarding it, and
    return the answer with the reasoning removed (clean main reply).
    Handles closed + unclosed + orphan tags across the qwen3 <think> and
    <thinking>/<thought>/<reasoning>/<reflection>/<scratchpad> variants.
    Tag-based only -- structural, no English content matching."""
    if not text:
        return "", text
    low = text.lower()
    if not any(t in low for t in _THINK_OPENERS):
        return "", text
    thoughts: list[str] = []

    def _cap(m: "re.Match") -> str:
        thoughts.append((m.group(2) or "").strip())
        return ""
    answer = _THINK_CAP_RE.sub(_cap, text)
    m = _THINK_CAP_UNCLOSED_RE.search(answer)
    if m:
        thoughts.append((m.group(2) or "").strip())
        answer = _THINK_CAP_UNCLOSED_RE.sub("", answer)
    answer = _THINK_ORPHAN_RE.sub("", answer).strip()
    reasoning = "\n\n".join(t for t in thoughts if t).strip()
    return reasoning, answer


def _strip_think_tags(text: str) -> str:
    """Back-compat: return only the answer (reasoning discarded). Use
    _split_think_tags when the reasoning should be KEPT for a dropdown."""
    return _split_think_tags(text)[1]


def _casual_agent_label(target_name: str) -> str:
    """Map registered sub-agent name -> casual MiOS-convention label
    for SSE status emission + dropdown summaries. Operator binding:
    surface labels stay generic ('sub-agent' / role), the specific
    daemon name lives in event payloads + journal, not in the chat
    UI. Same agent can be renamed via mios.toml [agents.*] without
    leaking the old name to the operator's screen."""
    cfg = _AGENT_REGISTRY.get(target_name) or {}
    role = str(cfg.get("role") or "").strip().lower()
    if role:
        return f"{role}-agent"
    return "sub-agent"


def _extract_last_user_text(messages: list) -> str:
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if not isinstance(m, dict):
            continue
        if m.get("role") != "user":
            continue
        c = m.get("content") or ""
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    return part.get("text", "")
            return ""
        return c if isinstance(c, str) else ""
    return ""

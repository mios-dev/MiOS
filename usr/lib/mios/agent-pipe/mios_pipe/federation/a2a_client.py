# AI-hint: A2A PEER-CLIENT consumer half extracted VERBATIM from server.py (refactor R11 federation follow-up). Owns the half that turns _AGENT_REGISTRY from a static localhost SSOT into a federated discoverable agent network: the layered peer-registry read (_a2a_load_peers, vendor /usr < /etc < user, self-loop-excluded), the per-peer card probe + skill indexing + synthetic-DAG-agent registration (_a2a_probe_peer), the optional tailnet auto-discovery (_a2a_autodiscover_peers), the startup fan-out (_a2a_client_startup), the JSON-RPC message/send delegation to a chosen peer with reputation recording (_a2a_send_message_to_peer), the A2A Task-envelope text extractor (_a2a_extract_text), and the self-peer-loop guard / agent-card fetch / tailnet candidate discovery helpers (_a2a_self_peer_url, _a2a_fetch_card, _a2a_tailnet_candidates). Moved byte-identically; server.py re-imports every name under its original alias (surface-parity zero-diff) and the @app /v1/a2a/dispatch route + the peer-discovery startup on_event stay THIN in server.py calling these names. _a2a_principal_metadata imports from mios_a2a, _mcp_render_headers from mios_mcp and loads_lenient from mios_jsonsalvage directly; every server-resident dep (the live _A2A_PEERS/_A2A_PEER_SKILLS registries + lock, the outbound _A2A_REPUTATION, _AGENT_REGISTRY, the peer-registry paths + A2A_COUNCIL/A2A_SELF_ID scalars, the HTTP client factory, and the worker-tool-surface cache invalidator) is dependency-INJECTED via configure(). This module NEVER imports server.
# AI-related: ./server.py, ./mios_config.py, ./mios_a2a.py, ./mios_mcp.py, ./mios_jsonsalvage.py, ./test_mios_a2a_client.py
# AI-functions: _a2a_self_peer_url, _a2a_fetch_card, _a2a_tailnet_candidates, _a2a_load_peers, _a2a_probe_peer, _a2a_autodiscover_peers, _a2a_client_startup, _a2a_send_message_to_peer, _a2a_extract_text, configure
"""A2A peer-client consumer half for the agent-pipe (refactor R11 follow-up).

Extracted VERBATIM from ``server.py`` -- the consumer half of the A2A
federation: the layered peer-registry read, the per-peer agent-card probe +
skill indexing, the optional tailnet auto-discovery, the startup fan-out, the
JSON-RPC ``message/send`` delegation to a chosen peer (with peer-reputation
recording), and the A2A Task-envelope text extractor. Every name is moved
byte-identically and re-imported by ``server.py``; the @app /v1/a2a/dispatch
route and the peer-discovery startup on_event stay there as thin wrappers, so
the module's public + HTTP surface is unchanged.

``_a2a_principal_metadata`` imports from :mod:`mios_a2a`,
``_mcp_render_headers`` from :mod:`mios_mcp` and ``loads_lenient`` from
:mod:`mios_jsonsalvage` directly. The self-peer-loop guard / agent-card fetch /
tailnet candidate discovery helpers live HERE (``_a2a_self_peer_url`` /
``_a2a_fetch_card`` / ``_a2a_tailnet_candidates``). Every remaining
server-resident dependency -- the live ``_A2A_PEERS`` / ``_A2A_PEER_SKILLS``
registries + lock, the outbound ``_A2A_REPUTATION``, the ``_AGENT_REGISTRY``,
the peer-registry paths + ``A2A_COUNCIL`` / ``A2A_SELF_ID`` scalars, the HTTP
client factory, and the worker-tool-surface cache invalidator -- is injected via
:func:`configure` (one-way boundary: this module never imports ``server``).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
import logging
from typing import Optional

import httpx

from mios_a2a import _a2a_principal_metadata
from mios_mcp import _mcp_render_headers
from mios_jsonsalvage import loads_lenient as _loads_lenient

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam -------------------------------------------
# The consumer half calls back into server-resident state/helpers: the live A2A
# peer registries + lock, the outbound peer-reputation tracker, the agent
# registry, the layered peer-registry paths, the council/self-id scalars,
# the HTTP client factory, and the worker-tool-surface cache invalidator (a
# newly-discovered peer registers a synthetic DAG agent -> server's
# _WORKER_TOOLS_FULL_CACHE must drop so it rebuilds; the module cannot rebind
# that server global across the one-way boundary). server.py calls configure()
# with all of them AFTER each is defined. Mutable containers (_A2A_PEERS/
# _A2A_PEER_SKILLS/_AGENT_REGISTRY) are injected BY REFERENCE so server-side
# mutation stays visible. Placeholders keep a standalone ``import
# mios_a2a_client`` working for the unit tests; nothing fires before configure()
# runs (handlers are only reached at request/startup time).
_A2A_PEERS: dict = {}
_A2A_PEER_SKILLS: dict = {}
_A2A_PEERS_LOCK = None
_A2A_REPUTATION = None
_AGENT_REGISTRY: dict = {}
_A2A_PEER_REGISTRY_PATHS: list = []
A2A_COUNCIL = False
A2A_SELF_ID = "local-mios"
# FED-G7 (T-051): when set, a discovered peer's FULL published AgentCard skills[]
# (name/description/tags) is attached to its synthetic registry entry as
# ``card_skills`` so the fan-out relevance model (mios_fanout) can route on the
# advertised skill, not just the collapsed strength-token ids. SSOT
# [a2a].route_on_card_skills; default OFF -> the peer entry is byte-identical.
ROUTE_ON_CARD_SKILLS = False
_get_client = None


def _invalidate_worker_cache() -> None:
    """Default no-op until server injects its _WORKER_TOOLS_FULL_CACHE invalidator."""
    return None


def configure(*, a2a_peers=None, a2a_peer_skills=None, a2a_peers_lock=None,
              a2a_reputation=None, agent_registry=None,
              a2a_peer_registry_paths=None, a2a_council=None, a2a_self_id=None,
              get_client=None, route_on_card_skills=None,
              invalidate_worker_cache=None) -> None:
    """Inject server.py's runtime deps. Mutable registries (_A2A_PEERS/
    _A2A_PEER_SKILLS/_AGENT_REGISTRY) are injected BY REFERENCE so server-side
    mutation stays visible to the probe + dispatch paths."""
    g = globals()
    if a2a_peers is not None:
        g["_A2A_PEERS"] = a2a_peers
    if a2a_peer_skills is not None:
        g["_A2A_PEER_SKILLS"] = a2a_peer_skills
    if a2a_peers_lock is not None:
        g["_A2A_PEERS_LOCK"] = a2a_peers_lock
    if a2a_reputation is not None:
        g["_A2A_REPUTATION"] = a2a_reputation
    if agent_registry is not None:
        g["_AGENT_REGISTRY"] = agent_registry
    if a2a_peer_registry_paths is not None:
        g["_A2A_PEER_REGISTRY_PATHS"] = a2a_peer_registry_paths
    if a2a_council is not None:
        g["A2A_COUNCIL"] = a2a_council
    if a2a_self_id is not None:
        g["A2A_SELF_ID"] = a2a_self_id
    if get_client is not None:
        g["_get_client"] = get_client
    if route_on_card_skills is not None:
        g["ROUTE_ON_CARD_SKILLS"] = route_on_card_skills
    if invalidate_worker_cache is not None:
        g["_invalidate_worker_cache"] = invalidate_worker_cache


def _a2a_self_peer_url(url: str) -> bool:
    """True if a peer URL is THIS orchestrator (loopback :8640). Delegating or
    fanning out to it re-enters the pipe and recurses UNBOUNDED -- the per-request
    recursion bound is process-local and does NOT cross the a2a HTTP hop (operator
 dGPU runaway: ~35 native-loop turns/sec pegged the GPU). The
    A2A_SELF_ID guard missed it because mios-a2a-discover registers the self as
    "mios-local" while A2A_SELF_ID defaults to "local-mios" -- an id mismatch. So
    exclude by URL (id-agnostic). Only LOOPBACK :8640 is self; a remote node on
    :8640 (real host/tailnet IP) is a legitimate peer and is NOT excluded."""
    _self_port = str(os.environ.get("MIOS_PORT_AGENT_PIPE", "8640")).strip()
    u = (url or "").lower()
    return (f":{_self_port}" in u) and (
        "127.0.0.1" in u or "localhost" in u or "://[::1]" in u or "0.0.0.0" in u)


async def _a2a_fetch_card(url: str, headers: dict,
                          timeout_s: float = 10.0) -> dict:
    """Try the spec's 0.3 well-known path, fall back to the legacy and the
    /v1 alias so we discover MiOS-flavoured peers AND clean A2A 0.3 peers.
    Returns the parsed card dict, or {"error": …}."""
    candidates = [
        url.rstrip("/") + "/.well-known/agent-card.json",
        url.rstrip("/") + "/.well-known/agent.json",
        url.rstrip("/") + "/v1/agent-card",
    ]
    h = _mcp_render_headers(headers or {})
    h.setdefault("Accept", "application/json")
    last_err: Optional[str] = None
    client = await _get_client()
    for candidate in candidates:
        try:
            r = await client.get(candidate, headers=h, timeout=timeout_s)
        except httpx.HTTPError as e:
            last_err = f"http error at {candidate}: {e}"
            continue
        if r.status_code != 200:
            last_err = f"{r.status_code} at {candidate}"
            continue
        try:
            card = r.json()
        except (json.JSONDecodeError, ValueError):
            last_err = f"non-JSON card at {candidate}"
            continue
        if isinstance(card, dict):
            card["_fetched_from"] = candidate
            return card
        last_err = f"card not an object at {candidate}"
    return {"error": last_err or "no card endpoint responded"}


async def _a2a_tailnet_candidates() -> list:
    """Candidate base-URLs to probe for an A2A agent-card: every ONLINE tailnet
    peer at the agent-pipe port (`tailscale status --json`) + any explicit
    MIOS_A2A_DISCOVER_URLS. Best-effort -- if the tailscale CLI is unreachable
    from the agent uid, only the explicit list is used. SSOT: the mios.toml
    [a2a] block feeds MIOS_A2A_DISCOVER_PORT / MIOS_A2A_DISCOVER_URLS via the
    userenv slot (no hardcoded node IPs in code)."""
    try:
        port = int(os.environ.get("MIOS_A2A_DISCOVER_PORT", "8640") or 8640)
    except ValueError:
        port = 8640
    urls: list = []
    for u in (os.environ.get("MIOS_A2A_DISCOVER_URLS", "") or "").split(","):
        u = u.strip().rstrip("/")
        if u:
            urls.append(u)
    try:
        p = await asyncio.create_subprocess_exec(
            "tailscale", "status", "--json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(p.communicate(), timeout=6)
        data = _loads_lenient((out or b"").decode("utf-8", "replace") or "{}")
        for peer in (data.get("Peer") or {}).values():    # Peer = OTHERS, not Self
            if not isinstance(peer, dict) or not peer.get("Online"):
                continue
            for ip in (peer.get("TailscaleIPs") or [])[:1]:   # first (v4) IP
                if ip:
                    urls.append(f"http://{ip}:{port}")
    except Exception as e:  # noqa: BLE001
        log.debug("a2a discover: tailscale status unavailable: %s", e)
    seen: set = set(); out_urls: list = []
    for u in urls:
        if u not in seen:
            seen.add(u); out_urls.append(u)
    return out_urls


def _a2a_load_peers() -> list:
    """Layered peer registry read: vendor < /etc < user. Later overlays
    REPLACE earlier entries with the same id (matches MCP client semantics)
    so an operator can disable a vendor peer by re-declaring it disabled.
    The LOCAL self-peer (loopback :8640) is EXCLUDED -- it is a self-loop vector
    (see _a2a_self_peer_url); delegation to oneself is a no-op on a single node."""
    by_id: dict = {}
    for p in _A2A_PEER_REGISTRY_PATHS:
        try:
            with open(p) as f:
                d = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            continue
        for s in (d.get("peers") or []):
            if not isinstance(s, dict):
                continue
            pid = str(s.get("id") or s.get("peer_id") or "").strip()
            if not pid:
                continue
            if _a2a_self_peer_url(str(s.get("url") or "")):
                log.info("a2a: excluding self-peer %r (%s) -- local orchestrator, "
                         "would self-loop", pid, s.get("url"))
                continue
            by_id[pid] = s
    return list(by_id.values())


async def _a2a_probe_peer(cfg: dict) -> None:
    """Fetch ONE peer's agent card, index its declared skills. Errors land in
    the per-peer state dict (never raise) so a single bad peer doesn't break
    startup -- mirrors _mcp_probe_server's contract."""
    pid = str(cfg.get("id") or cfg.get("peer_id") or "").strip()
    if not pid:
        return
    url = (cfg.get("url") or cfg.get("base_url") or "").rstrip("/") or ""
    state: dict = {"id": pid, "url": url, "status": "connecting",
                   "label": cfg.get("label") or pid,
                   "card": None, "skills": [],
                   "headers_template": cfg.get("headers") or {}}
    async with _A2A_PEERS_LOCK:
        _A2A_PEERS[pid] = state

    if not cfg.get("enabled", True):
        state["status"] = "disabled"
        return
    if not url:
        state["status"] = "config-error"
        state["error"] = "missing url"
        return

    card = await _a2a_fetch_card(url, cfg.get("headers") or {})
    if card.get("error"):
        state["status"] = "card-fetch-failed"
        state["error"] = card["error"]
        log.warning("a2a client: card fetch failed for %s: %s",
                    pid, state["error"])
        return
    state["card"] = card
    # LIBERAL on input: a v0.3 card carries a top-level protocolVersion; a v1.0
    # card moved it into supportedInterfaces[].protocolVersion (first = preferred).
    state["protocolVersion"] = card.get("protocolVersion") or next(
        (i.get("protocolVersion")
         for i in (card.get("supportedInterfaces") or [])
         if isinstance(i, dict) and i.get("protocolVersion")), None)
    state["agent_name"] = card.get("name")
    skills = []
    if isinstance(card.get("skills"), list):
        for s in card["skills"]:
            if isinstance(s, dict) and s.get("id"):
                skills.append({
                    "id": str(s.get("id")),
                    "name": s.get("name"),
                    "description": s.get("description"),
                    "tags": s.get("tags") or [],
                })
    state["skills"] = skills

    async with _A2A_PEERS_LOCK:
        # Rebuild this peer's skill index entries (clear stale first).
        for sid in list(_A2A_PEER_SKILLS.keys()):
            _A2A_PEER_SKILLS[sid] = [
                p for p in _A2A_PEER_SKILLS[sid] if p != pid]
            if not _A2A_PEER_SKILLS[sid]:
                _A2A_PEER_SKILLS.pop(sid, None)
        for s in skills:
            sid = s["id"]
            _A2A_PEER_SKILLS.setdefault(sid, []).append(pid)
    state["status"] = "ready"
    # Expose this peer as a synthetic DAG-routable agent + drop the worker tool
    # cache so the federated agent joins the roster (P0).
    try:
        # fanout default False (concurrent-swarm speed fix):
        # A2A peers are EXPLICIT-delegation-only, because with fanout=True the
        # pipe's OWN card (the local self-loop) joined every swarm -> the pipe
        # called ITSELF over A2A = pure overhead. Phase-4 opt-in : when
        # [a2a].council=true, every DISCOVERED peer EXCEPT the local self joins the
        # concurrent fan-out as a remote worker (the "spread across all nodes"
        # vision) -- the self is still excluded so the self-loop never returns.
        _a2a_fanout = bool(A2A_COUNCIL and (pid or "").strip().lower() != A2A_SELF_ID)
        _peer_cfg = {
            "endpoint": "", "model": pid, "role": "general",
            "default": False, "lane": "remote", "fanout": _a2a_fanout,
            "a2a_peer_id": pid, "research_only": False, "engines": {},
            "strengths": [str(s.get("id") or "") for s in (skills or [])],
        }
        # FED-G7 (T-051, flag-gated): keep the peer's FULL published skills[] so the
        # fan-out relevance model can route on the advertised name/description/tags,
        # not just the strength-token ids above. OFF -> entry is byte-identical.
        if ROUTE_ON_CARD_SKILLS and skills:
            _peer_cfg["card_skills"] = skills
        _AGENT_REGISTRY[f"a2a:{pid}"] = _peer_cfg
        _invalidate_worker_cache()
    except Exception:  # noqa: BLE001
        pass
    log.info("a2a client: %s ready (%d skills, protocol %s)",
             pid, len(skills), state.get("protocolVersion"))


async def _a2a_autodiscover_peers(known_urls: set) -> list:
    """Probe tailnet/explicit candidate URLs for an A2A agent-card; return peer
    cfgs for responders (skip URLs already in the registry, skip non-cards). So
    a NEW MiOS agent-pipe node auto-joins the mesh with zero registry editing
. OFF unless MIOS_A2A_TAILNET_DISCOVER is truthy; never
    raises; fast-fails on the compute-only nodes (ollama/oscontrol) that 404 the
    card."""
    if os.environ.get("MIOS_A2A_TAILNET_DISCOVER", "").strip().lower() \
            not in {"1", "true", "yes"}:
        return []
    cands = [u for u in await _a2a_tailnet_candidates()
             if u.rstrip("/") not in known_urls]
    if not cands:
        return []
    log.info("a2a autodiscover: probing %d tailnet candidate(s)", len(cands))

    async def _probe(url: str) -> Optional[dict]:
        card = await _a2a_fetch_card(url, {}, timeout_s=5.0)
        if not isinstance(card, dict) or card.get("error"):
            return None
        name = str(card.get("name") or card.get("agent_name") or "").strip()
        pid = (str(card.get("id") or "").strip()
               or "auto-" + url.split("//", 1)[-1].replace(":", "-").replace("/", ""))
        return {"id": pid, "url": url, "label": name or pid,
                "_autodiscovered": True}

    found = await asyncio.gather(*(_probe(u) for u in cands),
                                 return_exceptions=True)
    return [c for c in found if isinstance(c, dict)]


async def _a2a_client_startup() -> None:
    """Read the peer registry (+ optional tailnet auto-discovery), probe every
    enabled peer concurrently. Errors per peer are captured in state; total
    startup never blocks on a slow peer."""
    if os.environ.get("MIOS_A2A_CLIENT_DISABLED",
                      "").strip().lower() in {"1", "true", "yes"}:
        log.info("a2a client: disabled by env (MIOS_A2A_CLIENT_DISABLED)")
        return
    peers = _a2a_load_peers()
    _known = {str((p.get("url") or "")).rstrip("/") for p in peers}
    _disc = await _a2a_autodiscover_peers(_known)
    if _disc:
        log.info("a2a autodiscover: +%d tailnet peer(s)", len(_disc))
        peers = peers + _disc
    if not peers:
        log.info("a2a client: registry empty + no tailnet peers discovered")
        return
    log.info("a2a client: probing %d peer(s) (%d registry + %d discovered)",
             len(peers), len(peers) - len(_disc), len(_disc))
    await asyncio.gather(*(_a2a_probe_peer(s) for s in peers),
                         return_exceptions=True)


async def _a2a_send_message_to_peer(peer_id: str, text: str,
                                    context_id: Optional[str] = None,
                                    timeout_s: float = 120.0) -> dict:
    """POST a JSON-RPC message/send to one A2A peer's /a2a endpoint and return
    the Task envelope (or {"error": …}). Used by /v1/a2a/dispatch + the
    upcoming P2.2 live agent-to-agent delegation path."""
    async with _A2A_PEERS_LOCK:
        peer = _A2A_PEERS.get(peer_id)
    if not peer:
        return {"error": f"unknown A2A peer: {peer_id}"}
    if peer.get("status") != "ready":
        return {"error": f"peer {peer_id} not ready ({peer.get('status')})"}
    url = (peer.get("url") or "").rstrip("/") + "/a2a"
    headers = _mcp_render_headers(peer.get("headers_template") or {})
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Accept", "application/json")
    # v1.0 Message: role=ROLE_USER, a text Part by member presence (no `kind` tag).
    msg = {
        "role": "ROLE_USER",
        "messageId": uuid.uuid4().hex,
        "parts": [{"text": str(text or ""), "mediaType": "text/plain"}],
    }
    if context_id:
        msg["contextId"] = context_id
    # #60 WS-6: attach the signed delegation principal (no-op when no passport key)
    _pp = _a2a_principal_metadata(text, peer_id, context_id)
    if _pp:
        msg["metadata"] = {**(msg.get("metadata") or {}), "mios_principal": _pp}
    body = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) & 0x7FFFFFFF,
        "method": "message/send",
        "params": {"message": msg},
    }
    # Single exit so the delegation outcome is recorded once for peer reputation
    # (#54): result carries "error" on any failure, else the peer's Task envelope.
    result: dict
    try:
        client = await _get_client()
        r = await client.post(url, json=body, headers=headers,
                              timeout=timeout_s)
    except httpx.HTTPError as e:
        result = {"error": f"http error: {e}", "peer_id": peer_id}
    else:
        if r.status_code != 200:
            result = {"error": f"status {r.status_code}: {(r.text or '')[:200]}",
                      "peer_id": peer_id}
        else:
            try:
                resp = r.json()
            except (json.JSONDecodeError, ValueError):
                result = {"error": "non-JSON response", "peer_id": peer_id}
            else:
                if resp.get("error"):
                    err = resp["error"]
                    result = {"error": err.get("message") or "rpc error",
                              "code": err.get("code"), "peer_id": peer_id}
                else:
                    # LIBERAL on input: v1.0 wraps the SendMessage result in a
                    # SendMessageResponse oneof ({"task"|"message": ...}); v0.3
                    # returned the bare Task. Unwrap when wrapped, else take as-is,
                    # so the returned envelope is always the Task/Message itself.
                    res = resp.get("result")
                    if isinstance(res, dict):
                        result = res.get("task") or res.get("message") or res
                    else:
                        result = {}
    _A2A_REPUTATION.record(
        peer_id, not (isinstance(result, dict) and result.get("error")))
    return result


def _a2a_extract_text(env: dict) -> str:
    """Pull the assistant text out of an A2A Task envelope (artifacts[].parts[]
    or status.message.parts[]) -- _a2a_send_message_to_peer returns the raw Task
 object, not plain text (P0)."""
    if not isinstance(env, dict) or env.get("error"):
        return ""
    def _parts(parts):
        return "".join(str(p.get("text") or "") for p in (parts or [])
                       if isinstance(p, dict))
    for art in (env.get("artifacts") or []):
        t = _parts(art.get("parts"))
        if t.strip():
            return t.strip()
    msg = ((env.get("status") or {}).get("message")) or env.get("message") or {}
    return _parts(msg.get("parts")).strip()

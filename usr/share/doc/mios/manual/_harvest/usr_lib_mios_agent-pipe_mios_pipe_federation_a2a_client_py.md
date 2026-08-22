<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### A2A peer-client consumer half for the agent-pipe (refactor...

A2A peer-client consumer half for the agent-pipe (refactor R11 follow-up).

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

<!-- mios-src:a5096accbfb4 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:3-24 -->

### True if a peer URL is THIS orchestrator (loopback :8640)....

True if a peer URL is THIS orchestrator (loopback :8640). Delegating or
    fanning out to it re-enters the pipe and recurses UNBOUNDED -- the per-request
    recursion bound is process-local and does NOT cross the a2a HTTP hop (operator
 dGPU runaway: ~35 native-loop turns/sec pegged the GPU). The
    A2A_SELF_ID guard missed it because mios-a2a-discover registers the self as
    "mios-local" while A2A_SELF_ID defaults to "local-mios" -- an id mismatch. So
    exclude by URL (id-agnostic). Only LOOPBACK :8640 is self; a remote node on
    :8640 (real host/tailnet IP) is a legitimate peer and is NOT excluded.

<!-- mios-src:f235ade235ad from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:97-104 -->

### Candidate base-URLs to probe for an A2A agent-card: every...

Candidate base-URLs to probe for an A2A agent-card: every ONLINE tailnet
    peer at the agent-pipe port (`tailscale status --json`) + any explicit
    MIOS_A2A_DISCOVER_URLS. Best-effort -- if the tailscale CLI is unreachable
    from the agent uid, only the explicit list is used. SSOT: the mios.toml
    [a2a] block feeds MIOS_A2A_DISCOVER_PORT / MIOS_A2A_DISCOVER_URLS via the
    userenv slot (no hardcoded node IPs in code).

<!-- mios-src:54b4f984c03e from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:223-228 -->

### Layered peer registry read

Layered peer registry read: vendor < /etc < user. Later overlays
    REPLACE earlier entries with the same id (matches MCP client semantics)
    so an operator can disable a vendor peer by re-declaring it disabled.
    The LOCAL self-peer (loopback :8640) is EXCLUDED -- it is a self-loop vector
    (see _a2a_self_peer_url); delegation to oneself is a no-op on a single node.

<!-- mios-src:ecedcd420174 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:260-264 -->

### Probe tailnet/explicit candidate URLs for an A2A...

Probe tailnet/explicit candidate URLs for an A2A agent-card; return peer
    cfgs for responders (skip URLs already in the registry, skip non-cards). So
    a NEW MiOS agent-pipe node auto-joins the mesh with zero registry editing
. OFF unless MIOS_A2A_TAILNET_DISCOVER is truthy; never
    raises; fast-fails on the compute-only nodes (e.g. oscontrol) that 404 the
    card.

<!-- mios-src:0371e1296483 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:366-371 -->

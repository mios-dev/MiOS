<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: A2A PEER-CLIENT consumer half extracted VERBATIM from server.py (refactor R11 federation follow-up). Owns the half that turns _AGENT_REGISTRY from a static localhost SSOT into a federated discoverable agent network: the layered peer-registry read (_a2a_load_peers, vendor /usr < /etc < user, self-loop-excluded), the per-peer card probe + skill indexing + synthetic-DAG-agent registration (_a2a_probe_peer), the optional tailnet auto-discovery (_a2a_autodiscover_peers), the startup fan-out (_a2a_client_startup), the JSON-RPC message/send delegation to a chosen peer with reputation recording (_a2a_send_message_to_peer), the A2A Task-envelope text extractor (_a2a_extract_text), and the self-peer-loop guard / agent-card fetch / tailnet candidate discovery helpers (_a2a_self_peer_url, _a2a_fetch_card, _a2a_tailnet_candidates). Moved byte-identically; server.py re-imports every name under its original alias (surface-parity zero-diff) and the @app /v1/a2a/dispatch route + the peer-discovery startup on_event stay THIN in server.py calling these names. _a2a_principal_metadata imports from mios_a2a, _mcp_render_headers from mios_mcp and loads_lenient from mios_jsonsalvage directly; every server-resident dep (the live _A2A_PEERS/_A2A_PEER_SKILLS registries + lock, the outbound _A2A_REPUTATION, _AGENT_REGISTRY, the peer-registry paths + A2A_COUNCIL/A2A_SELF_ID scalars, the HTTP client factory, and the worker-tool-surface cache invalidator) is dependency-INJECTED via configure(). This module NEVER imports server.
AI-related: ./server.py, ./mios_config.py, ./mios_a2a.py, ./mios_mcp.py, ./mios_jsonsalvage.py, ./test_mios_a2a_client.py
AI-functions: _a2a_self_peer_url, _a2a_fetch_card, _a2a_tailnet_candidates, _a2a_load_peers, _a2a_probe_peer, _a2a_autodiscover_peers, _a2a_client_startup, _a2a_send_message_to_peer, _a2a_extract_text, configure

<!-- mios-src:f7d1488609e2 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:1-3 -->


<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A18 federated agent discovery -- the PURE epidemic-gossip + SWIM-style anti-entropy core (the transport-free half; mios_reputation already scores peers, this adds the discovery algorithm). Deterministic, stdlib-only so it unit-tests in isolation: select_gossip_peers (seeded fanout pick -> reproducible per round, no Math.random), merge_peer/merge_peer_set (SWIM incarnation = heartbeat: higher wins, TRUST-GATED so a rogue/low-reputation peer's rumors are rejected -- ties to mios_reputation), prune_dead (TTL eviction of unheard peers), digest (the id->heartbeat rumor vector for anti-entropy). server.py owns the actual UDP/HTTP gossip transport + the periodic round; this owns the convergence logic.
AI-related: ./mios_reputation.py, ./mios_a2a_principal.py, ./mios_crl.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_gossip.py
AI-functions: select_gossip_peers, merge_peer, merge_peer_set, prune_dead, digest, class Peer

<!-- mios-src:23092e059769 from usr/lib/mios/agent-pipe/mios_pipe/kernel/gossip.py:1-3 -->


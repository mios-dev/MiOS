<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_gossip -- federated agent discovery via epidemic...

mios_gossip -- federated agent discovery via epidemic gossip + anti-entropy
(WS-A18, the AIOS peer-discovery layer).

Pure stdlib. MiOS federates agents over A2A; mios_reputation scores peers but
there was no DISCOVERY mechanism -- how a node learns which peers exist and keeps
that set fresh + trustworthy without a central registry. This is the classic
answer: epidemic gossip (each round, push/pull rumors to a small random fanout)
with SWIM-style failure detection (an incrementing per-peer heartbeat /
incarnation; higher wins on merge; unheard peers age out by TTL).

Two MiOS-specific properties:
  * TRUST-GATED merge -- a peer rumor is only accepted if its trust (from
    mios_reputation, and gated by mios_crl revocation upstream) clears
    `min_trust`. This is the OWASP-Agentic "rogue agent / unauthorized
    delegation" defense applied to discovery: a low-reputation or revoked peer
    cannot inject itself (or poison the peer set) via gossip.
  * DETERMINISTIC selection -- `select_gossip_peers` is seeded (caller passes the
    round number), so a round is reproducible + unit-testable; no global RNG.

server.py owns the transport (push the `digest()` to the selected peers, pull
theirs, `merge_peer_set` the response) + the periodic round + wiring trust to
mios_reputation; this module owns the deterministic convergence math.

<!-- mios-src:58549bf3c205 from usr/lib/mios/agent-pipe/mios_pipe/kernel/gossip.py:3-25 -->

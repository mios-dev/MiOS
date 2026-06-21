# AI-hint: WS-A18 federated agent discovery -- the PURE epidemic-gossip + SWIM-style anti-entropy core (the transport-free half; mios_reputation already scores peers, this adds the discovery algorithm). Deterministic, stdlib-only so it unit-tests in isolation: select_gossip_peers (seeded fanout pick -> reproducible per round, no Math.random), merge_peer/merge_peer_set (SWIM incarnation = heartbeat: higher wins, TRUST-GATED so a rogue/low-reputation peer's rumors are rejected -- ties to mios_reputation), prune_dead (TTL eviction of unheard peers), digest (the id->heartbeat rumor vector for anti-entropy). server.py owns the actual UDP/HTTP gossip transport + the periodic round; this owns the convergence logic.
# AI-related: ./mios_reputation.py, ./mios_a2a_principal.py, ./mios_crl.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_gossip.py
# AI-functions: select_gossip_peers, merge_peer, merge_peer_set, prune_dead, digest, class Peer
"""mios_gossip -- federated agent discovery via epidemic gossip + anti-entropy
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
"""

from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional, Sequence


class Peer:
    """A discovered peer. `heartbeat` is the SWIM incarnation (monotonic per
    peer); `last_seen` is local wall-clock of the last accepted rumor; `trust` is
    the cached reputation at merge time (advisory)."""

    __slots__ = ("id", "endpoint", "heartbeat", "last_seen", "trust")

    def __init__(self, id: str, endpoint: str = "", heartbeat: int = 0,
                 last_seen: float = 0.0, trust: float = 1.0) -> None:
        self.id = str(id)
        self.endpoint = str(endpoint)
        self.heartbeat = int(heartbeat)
        self.last_seen = float(last_seen)
        self.trust = float(trust)

    def to_dict(self) -> dict:
        return {"id": self.id, "endpoint": self.endpoint,
                "heartbeat": self.heartbeat, "last_seen": round(self.last_seen, 3),
                "trust": round(self.trust, 4)}


def _rank(seed: object, peer_id: str) -> str:
    """Stable per-(round, peer) rank key -> deterministic shuffle without a global
    RNG (so a gossip round is reproducible + testable)."""
    return hashlib.sha256(f"{seed}:{peer_id}".encode()).hexdigest()


def select_gossip_peers(peer_ids: Sequence[str], fanout: int, *, seed: object,
                        exclude: "Optional[Sequence[str]]" = None) -> List[str]:
    """Pick up to `fanout` peers to gossip with this round. Deterministic given
    `seed` (pass the round number/id) so rounds rotate coverage + are testable.
    `exclude` drops self / already-contacted ids."""
    ex = set(exclude or ())
    cands = sorted({str(p) for p in peer_ids if str(p) not in ex},
                   key=lambda p: _rank(seed, p))
    return cands[:max(0, int(fanout))]


def merge_peer(local: "Dict[str, Peer]", incoming: Peer, *, now: float,
               min_trust: float = 0.0,
               trust_of: "Optional[Callable[[str], float]]" = None) -> bool:
    """SWIM-style trust-gated merge of ONE incoming rumor into `local`. Returns
    True if accepted (new peer or strictly higher heartbeat). REJECTS (False)
    when the peer's trust < `min_trust` (rogue/revoked -> cannot enter or refresh
    the set). `trust_of(id)` (e.g. mios_reputation lookup) overrides the rumor's
    self-reported trust when supplied."""
    pid = str(incoming.id)
    if not pid:
        return False
    trust = trust_of(pid) if trust_of is not None else float(incoming.trust)
    if trust < float(min_trust):
        return False
    cur = local.get(pid)
    if cur is not None and int(incoming.heartbeat) <= cur.heartbeat:
        return False                      # stale/duplicate rumor -> ignore
    local[pid] = Peer(pid, incoming.endpoint or (cur.endpoint if cur else ""),
                      int(incoming.heartbeat), float(now), float(trust))
    return True


def merge_peer_set(local: "Dict[str, Peer]", incoming: "Sequence[Peer]", *,
                   now: float, min_trust: float = 0.0,
                   trust_of: "Optional[Callable[[str], float]]" = None) -> int:
    """Anti-entropy merge of a batch of rumors. Returns how many were accepted."""
    return sum(1 for p in (incoming or [])
               if merge_peer(local, p, now=now, min_trust=min_trust, trust_of=trust_of))


def prune_dead(local: "Dict[str, Peer]", *, now: float, ttl: float,
               keep: "Optional[Sequence[str]]" = None) -> List[str]:
    """SWIM failure detection: drop peers not heard from within `ttl` seconds.
    `keep` (e.g. seed/bootstrap peers) are never pruned. Returns dropped ids."""
    kept = set(keep or ())
    dead = [pid for pid, p in local.items()
            if pid not in kept and (now - p.last_seen) > float(ttl)]
    for pid in dead:
        local.pop(pid, None)
    return dead


def digest(local: "Dict[str, Peer]") -> "Dict[str, int]":
    """The rumor digest to push/pull for anti-entropy: id -> heartbeat. The peer
    compares against its own and returns the deltas (newer rumors)."""
    return {pid: p.heartbeat for pid, p in local.items()}

#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_gossip (WS-A18 epidemic-gossip + SWIM anti-entropy discovery core). Pure stdlib, no server.py/DB/pytest. Verifies seeded deterministic peer selection (reproducible per round, fanout cap, exclude, coverage rotation across seeds), SWIM heartbeat merge (new accepted, higher-incarnation wins, stale/equal rejected), TRUST-GATED merge (low-reputation/revoked rumor rejected; trust_of override), batch merge count, TTL prune with keep-list, and the anti-entropy digest.
# AI-related: ./mios_gossip.py
# AI-functions: check, main
"""Unit tests for mios_gossip (WS-A18 federated discovery)."""

import sys

import mios_gossip as g

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


IDS = list("abcdefgh")


def t_select():
    s1 = g.select_gossip_peers(IDS, 3, seed=1)
    s2 = g.select_gossip_peers(IDS, 3, seed=1)
    check("select: deterministic per seed", s1 == s2, str(s1))
    check("select: respects fanout", len(s1) == 3)
    check("select: subset of input", set(s1) <= set(IDS))
    check("select: fanout>n -> all", set(g.select_gossip_peers(IDS, 99, seed=1)) == set(IDS))
    check("select: exclude self/contacted", "a" not in g.select_gossip_peers(IDS, 8, seed=1, exclude=["a"]))
    # coverage rotates across rounds (not every seed picks the same 3)
    sels = {tuple(g.select_gossip_peers(IDS, 3, seed=s)) for s in range(8)}
    check("select: rotates coverage across seeds", len(sels) > 1)


def t_merge():
    local: dict = {}
    ok = g.merge_peer(local, g.Peer("p1", "u1", heartbeat=1, trust=1.0), now=100.0, min_trust=0.5)
    check("merge: new peer accepted", ok and "p1" in local and local["p1"].heartbeat == 1)
    check("merge: last_seen set", local["p1"].last_seen == 100.0)
    check("merge: equal heartbeat rejected", g.merge_peer(local, g.Peer("p1", heartbeat=1), now=200.0, min_trust=0.5) is False)
    check("merge: stale (lower) rejected", g.merge_peer(local, g.Peer("p1", heartbeat=0), now=200.0, min_trust=0.5) is False)
    up = g.merge_peer(local, g.Peer("p1", heartbeat=2), now=300.0, min_trust=0.5)
    check("merge: higher incarnation wins", up and local["p1"].heartbeat == 2 and local["p1"].last_seen == 300.0)
    check("merge: endpoint preserved when rumor omits it", local["p1"].endpoint == "u1")


def t_trust_gate():
    local: dict = {}
    check("trust: low-trust rumor rejected",
          g.merge_peer(local, g.Peer("rogue", heartbeat=9, trust=0.1), now=1.0, min_trust=0.5) is False
          and "rogue" not in local)
    check("trust: trust_of override rejects (revoked)",
          g.merge_peer(local, g.Peer("p2", heartbeat=1, trust=0.99), now=1.0, min_trust=0.5,
                       trust_of=lambda _id: 0.0) is False)
    check("trust: trust_of override accepts",
          g.merge_peer(local, g.Peer("p3", heartbeat=1, trust=0.0), now=1.0, min_trust=0.5,
                       trust_of=lambda _id: 0.9) is True and "p3" in local)


def t_merge_set_and_digest():
    local: dict = {}
    n = g.merge_peer_set(local, [g.Peer("a", heartbeat=1, trust=1.0),
                                 g.Peer("b", heartbeat=1, trust=0.2),   # gated out
                                 g.Peer("c", heartbeat=1, trust=1.0)],
                         now=5.0, min_trust=0.5)
    check("merge_set: accepts only trusted", n == 2 and set(local) == {"a", "c"})
    d = g.digest(local)
    check("digest: id->heartbeat map", d == {"a": 1, "c": 1})


def t_prune():
    local = {
        "fresh": g.Peer("fresh", heartbeat=1, last_seen=180.0, trust=1.0),
        "stale": g.Peer("stale", heartbeat=1, last_seen=10.0, trust=1.0),
        "seed":  g.Peer("seed", heartbeat=1, last_seen=0.0, trust=1.0),
    }
    dropped = g.prune_dead(local, now=200.0, ttl=50.0, keep=["seed"])
    check("prune: drops only the stale unheard peer", dropped == ["stale"])
    check("prune: keeps fresh + kept seed", set(local) == {"fresh", "seed"})


def main():
    t_select()
    t_merge()
    t_trust_gate()
    t_merge_set_and_digest()
    t_prune()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

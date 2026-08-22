<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Peer reputation for zero-trust A2A federation (#54). Tracks...

Peer reputation for zero-trust A2A federation (#54).

Tracks how reliably each A2A peer has handled delegations and ranks candidates so
a reliable peer is chosen over a flaky one. In-memory + per-process (like the
_A2A_PEERS registry it complements -- both rebuild on restart); persistence is a
later concern. Pure logic, no I/O, no server import.

Scoring is Laplace-smoothed success rate: (ok + 1) / (ok + bad + 2). No history ->
0.5 (neutral). A recent-failure penalty (consecutive_bad) lets a peer that just
started failing drop quickly without waiting for its long-run average to move.

<!-- mios-src:c577b95395e3 from usr/lib/mios/agent-pipe/mios_pipe/identity/reputation.py:3-13 -->

### Load persisted counter rows back into state (REPLACING...

Load persisted counter rows back into state (REPLACING current), so
        reputation survives a restart. The inverse of rows(). Degrade-open: a
        malformed row is skipped (a bad row never wipes the rest).

<!-- mios-src:63a939dc0f53 from usr/lib/mios/agent-pipe/mios_pipe/identity/reputation.py:73-75 -->

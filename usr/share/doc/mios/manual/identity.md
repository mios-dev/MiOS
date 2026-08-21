<!-- AI-hint: Manual pages distilled from the source comments of identity, sanitized, each passage anchored to the comment it came from. -->

# identity

### mios_crl -- token/cert revocation list (WS-A10, the AIOS...

mios_crl -- token/cert revocation list (WS-A10, the AIOS edge revocation layer).

Pure stdlib. A small, explicit revocation set the principal verifier consults so
a credential can be killed BEFORE it expires (a compromised token, a retired
peer). The operator/SSOT owns the source list; this holds it + answers
is_revoked. Membership is O(1); empty CRL == nothing revoked (the no-op default).

<!-- mios-src:ef32b6d4c7c7 from usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py:4-9 -->

### Build a CRL from a list, or a dict carrying a `revoked`...

Build a CRL from a list, or a dict carrying a `revoked` list (the
        caller-tokens.json shape). Anything else -> an empty CRL (degrade-open
        on a malformed source: a broken CRL must not block every caller).

<!-- mios-src:a7e52f4bb9bc from usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py:46-48 -->

### Pure helpers for the #60 WS-6 signed delegation principal...

Pure helpers for the #60 WS-6 signed delegation principal (A2A).

Why a sibling module: the crypto primitives (Ed25519 sign/verify) and the request
principal live in server.py, but the CLAIM SHAPE + the text-binding + the
metadata routing are deterministic logic that should be tested without importing
the orchestrator. The caller injects sign_fn(table, fields)->envelope|None and
verify_fn(envelope, (table, fields))->(ok, reason); this module supplies the
contract those two sides must agree on.

Rides A2A's message.metadata extension point under the key "mios_principal", so a
non-MiOS peer simply ignores it. Degrade-open: with no key the claims still ride
along but unsigned (passport=None), and the verifier reports "unsigned".

<!-- mios-src:4ed4bee8554a from usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py:4-16 -->

### Receive-side check. Returns (verdict, reason, claims)...

Receive-side check. Returns (verdict, reason, claims):
      verdict None  -> no principal block present (legacy / non-MiOS peer)
      verdict False -> tampered text, unsigned, or bad signature
      verdict True  -> signature valid AND the delivered text matches the claim
    The text-digest check runs BEFORE signature verification, so a swapped
    instruction fails even when carrying an otherwise-valid envelope.

<!-- mios-src:587c80d85c55 from usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py:63-68 -->

### Peer reputation for zero-trust A2A federation (#54). Tracks...

Peer reputation for zero-trust A2A federation (#54).

Tracks how reliably each A2A peer has handled delegations and ranks candidates so
a reliable peer is chosen over a flaky one. In-memory + per-process (like the
_A2A_PEERS registry it complements -- both rebuild on restart); persistence is a
later concern. Pure logic, no I/O, no server import.

Scoring is Laplace-smoothed success rate: (ok + 1) / (ok + bad + 2). No history ->
0.5 (neutral). A recent-failure penalty (consecutive_bad) lets a peer that just
started failing drop quickly without waiting for its long-run average to move.

<!-- mios-src:c577b95395e3 from usr/lib/mios/agent-pipe/mios_pipe/identity/reputation.py:4-14 -->

### Load persisted counter rows back into state (REPLACING...

Load persisted counter rows back into state (REPLACING current), so
        reputation survives a restart. The inverse of rows(). Degrade-open: a
        malformed row is skipped (a bad row never wipes the rest).

<!-- mios-src:63a939dc0f53 from usr/lib/mios/agent-pipe/mios_pipe/identity/reputation.py:74-76 -->

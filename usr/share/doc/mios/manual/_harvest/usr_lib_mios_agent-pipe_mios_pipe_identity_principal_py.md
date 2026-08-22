<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

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

<!-- mios-src:4ed4bee8554a from usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py:3-15 -->

### Receive-side check. Returns (verdict, reason, claims)...

Receive-side check. Returns (verdict, reason, claims):
      verdict None  -> no principal block present (legacy / non-MiOS peer)
      verdict False -> tampered text, unsigned, or bad signature
      verdict True  -> signature valid AND the delivered text matches the claim
    The text-digest check runs BEFORE signature verification, so a swapped
    instruction fails even when carrying an otherwise-valid envelope.

<!-- mios-src:587c80d85c55 from usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py:62-67 -->

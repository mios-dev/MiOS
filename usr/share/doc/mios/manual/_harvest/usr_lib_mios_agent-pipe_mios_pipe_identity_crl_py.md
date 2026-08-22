<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_crl -- token/cert revocation list (WS-A10, the AIOS...

mios_crl -- token/cert revocation list (WS-A10, the AIOS edge revocation layer).

Pure stdlib. A small, explicit revocation set the principal verifier consults so
a credential can be killed BEFORE it expires (a compromised token, a retired
peer). The operator/SSOT owns the source list; this holds it + answers
is_revoked. Membership is O(1); empty CRL == nothing revoked (the no-op default).

<!-- mios-src:ef32b6d4c7c7 from usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py:3-8 -->

### Build a CRL from a list, or a dict carrying a `revoked`...

Build a CRL from a list, or a dict carrying a `revoked` list (the
        caller-tokens.json shape). Anything else -> an empty CRL (degrade-open
        on a malformed source: a broken CRL must not block every caller).

<!-- mios-src:a7e52f4bb9bc from usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py:45-47 -->

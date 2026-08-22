<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### U3: the AgentCard `signatures[]` is a real A2A v1.0 JWS...

U3: the AgentCard `signatures[]` is a real A2A v1.0 JWS (RFC-7515 over RFC-8785
    JCS), proven with a real Ed25519 key -- the spec mandates JWS, so the proof is a
    cryptographic sign->verify round-trip, not just a shape check. A tampered card or
    tampered signature FAILS verification; a non-EdDSA alg is rejected; the protected
    header decodes to the JOSE-standard {alg: EdDSA, kid}. Skipped cleanly where
    python3-cryptography is absent (the build host), exactly like the passport
    real-key round-trip in test_mios_a2a_principal.

<!-- mios-src:606e0131d1ae from usr/lib/mios/agent-pipe/test_mios_a2a.py:147-153 -->

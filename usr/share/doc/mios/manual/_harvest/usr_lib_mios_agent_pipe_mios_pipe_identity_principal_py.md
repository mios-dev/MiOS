<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure A2A signed-delegation-principal helpers (#60 WS-6). Builds + verifies. Also HOSTS the low-level agent-passport Ed25519 crypto (canonical op-hash + sign/verify + keypair load/cache, moved verbatim from server.py) that the signed-principal contract here consumes through the injected sign_fn/verify_fn; server.py keeps the surface-pinned PASSPORT_* config consts and injects them via configure(). Still server.py-free (one-way DI boundary) and unit-testable in isolation; cryptography is imported lazily inside the helpers so a host without python3-cryptography still imports the module.
AI-related: server.py, mios_hitl, mios-passport, /usr/share/mios/mios.toml
AI-functions: text_digest, build_claims, build_metadata, verify, configure, _passport_canonical_json, _passport_op_hash, _passport_load_priv, _passport_kid, _passport_load_public, _passport_sign, _passport_verify

<!-- mios-src:6f85969cd87b from usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py:1-3 -->


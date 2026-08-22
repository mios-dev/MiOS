<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A10 certificate/token revocation list (CRL). Pure-stdlib revocation set: load revoked token-ids / principal-ids from a list (or a caller-tokens.json revoked[] block), check is_revoked(tid) at verify time, and revoke()/restore() at runtime. The agent-pipe's A2A caller-key gate (mios_a2a._caller_key_revoked) consults is_revoked so a compromised/retired credential is refused even before expiry. Pure (no fs/network -- the caller loads the source) so it unit-tests on the host.
AI-related: ./mios_a2a.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_crl.py
AI-functions: revoke, restore, is_revoked, load, merge, ids, class CRL

<!-- mios-src:6d0abe9064b4 from usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py:1-3 -->


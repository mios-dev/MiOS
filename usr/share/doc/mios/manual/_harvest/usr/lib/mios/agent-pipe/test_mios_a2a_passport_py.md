<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_a2a_principal (WS-6 signed...

Standalone unit test for mios_a2a_principal (WS-6 signed delegation principal).

Pure stdlib + the sibling module only -- no server.py / Ed25519 keys. The real
crypto is the agent passport's _passport_sign/_passport_verify (covered by the
passport tests + operator on MiOS-DEV); here we inject fakes to prove the
deterministic glue: claim shape, text-binding, and the absent/unsigned/tamper/ok
branches the receive path relies on.

Run:  python test_mios_a2a_passport.py

<!-- mios-src:4f4d61c2c0e4 from usr/lib/mios/agent-pipe/test_mios_a2a_passport.py:3-12 -->

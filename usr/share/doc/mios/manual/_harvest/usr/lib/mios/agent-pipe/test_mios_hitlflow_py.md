<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Stdlib assert-script for mios_hitlflow (R7 security wave)....

Stdlib assert-script for mios_hitlflow (R7 security wave).

Covers the security-critical decisions of the HITL ask-to-run + runtime
approval-gate flow:
  * _action_hash determinism + structural (key-order invariant) identity.
  * _pending_hash NULL-free, deterministic, per-action bypass key behavior
    (same action -> same key so an approval bypasses a later identical
    dispatch; a DIFFERENT action -> a DIFFERENT key so the approval never
    crosses over).
  * _hitl_gate NAME-KEYED gating using the REAL mios_secset high-privilege
    builder + the REAL mios_hitl decision helpers: a scoped high-privilege
    verb BLOCKS (gate mode, unapproved); a safe verb PROCEEDS.
  * _classify_approval_reply with a stubbed model returns approve / reject
    correctly (and degrades to 'unrelated' on error).

Run: python test_mios_hitlflow.py

<!-- mios-src:6f5103cf0f7c from usr/lib/mios/agent-pipe/test_mios_hitlflow.py:3-19 -->

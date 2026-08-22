<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for the #54 mTLS provisioning tool....

Standalone unit test for the #54 mTLS provisioning tool.

Provisions into a temp dir and verifies the PKI is correct: the agent leaf is
signed by the CA, it is valid for BOTH client + server auth, and re-running keeps
the existing CA (so exchanged peer trust is not invalidated). Needs cryptography;
SKIPS (exit 0) if it is unavailable so the drift-gate stays portable.

Run:  python test_mios_mtls.py

<!-- mios-src:bde353015183 from usr/lib/mios/agent-pipe/test_mios_mtls.py:3-11 -->

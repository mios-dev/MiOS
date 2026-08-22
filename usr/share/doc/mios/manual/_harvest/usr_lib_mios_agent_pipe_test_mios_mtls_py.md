<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for tools/provision-agent-mtls (#54 mTLS PKI): the agent leaf cert is signed by the CA, carries clientAuth+serverAuth EKU, and re-runs reuse the CA (peer trust survives). Skips cleanly if cryptography is absent.
AI-related: tools/provision-agent-mtls.py
AI-functions: _skip, _load_tool, t_chain, t_eku, t_ca_reuse, main

<!-- mios-src:b2d437ca4db1 from usr/lib/mios/agent-pipe/test_mios_mtls.py:1-3 -->


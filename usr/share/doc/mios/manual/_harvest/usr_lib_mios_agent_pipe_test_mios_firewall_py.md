<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone stdlib assert-script for mios_firewall (the provenance-taint + Semantic Firewall plane). Wires the module with the REAL mios_secset-derived taint/high-privilege sets + a stubbed _db_read, then proves the lethal-trifecta defense: _is_external_url host classification (external vs allowlist/internal/fail-safe), _classify_verb_taint NAME-KEYED taint introduction (web/open_url-external/powershell_run/text_view-system/mcp.*-taint vs read-only safe), the _session_is_tainted pg taint-chain reader (stubbed), and the firewall BLOCK decision (a tainted session blocks a high-privilege verb + the exfil/external open_url taint source, and allows a read-only verb). No server import.
AI-related: ./mios_firewall.py, ./mios_secset.py, ./test_server_import.py
AI-functions: (assert-script; no defs)

<!-- mios-src:8c2e1145b4dc from usr/lib/mios/agent-pipe/test_mios_firewall.py:1-3 -->


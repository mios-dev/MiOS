<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Provenance-taint + Semantic Firewall plane extracted verbatim from server.py (refactor R7 wave). Lethal-trifecta defense: a session that ingested EXTERNAL/untrusted content (external open_url, powershell_run output, system-path text_view, taint-declaring MCP tools, or the SSOT-opt-in web-fetch verbs) gets its tool_call rows tainted, and _session_is_tainted lets the caller's firewall BLOCK downstream high-privilege + exfiltration verbs in the same session. Holds _is_external_url (allowlist-host classifier, fail-safe External), _classify_verb_taint (per-verb taint introducer; NAME-KEYED on _TAINT_VERBS + the open_url/powershell_run/text_view/mcp.* heuristics) and _session_is_tainted (the pg taint-chain reader). SECURITY-CRITICAL: every verb key, heuristic and set-membership is moved byte-for-byte -- a silent gate-disable is the worst regression. The SSOT-derived _TAINT_VERBS set, the PROVENANCE_TAINT_ENABLE flag, the _ALLOWLIST_HOSTS host set, the _MCP_CLIENT_TOOLS registry and the _db_read pg reader are dependency-INJECTED via configure() (one-way boundary -- mios_firewall NEVER imports server). server.py re-imports every name under its EXACT original alias so the importable surface stays byte-identical.
AI-related: ./server.py, ./mios_secset.py, ./mios_pdp.py, ./mios_policy.py, ./test_mios_firewall.py
AI-functions: _is_external_url, _classify_verb_taint, _session_is_tainted, configure

<!-- mios-src:53fe5d2c759f from usr/lib/mios/agent-pipe/mios_pipe/access/firewall.py:1-3 -->


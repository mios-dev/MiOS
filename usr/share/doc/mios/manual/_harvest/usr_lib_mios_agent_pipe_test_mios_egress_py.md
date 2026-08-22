<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for tools/generate-egress-firewall (#54 egress firewall): build_ruleset emits a uid-scoped nftables ruleset with the always-allowed nets, per-mode final action (off=no-op, audit=log+accept, enforce=log+drop), and v4/v6 allowlist rules. Pure string assertions -- no nft binary needed (a separate nft -c check covers syntax on hosts that have it).
AI-related: tools/generate-egress-firewall.py
AI-functions: _check, _load_tool, t_always, t_modes, t_allow, t_scope, main

<!-- mios-src:f512ce88a296 from usr/lib/mios/agent-pipe/test_mios_egress.py:1-3 -->


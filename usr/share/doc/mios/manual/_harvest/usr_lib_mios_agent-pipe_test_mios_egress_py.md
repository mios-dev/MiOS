<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for the #54 egress-firewall generator....

Standalone unit test for the #54 egress-firewall generator.

Pure: asserts the structure of build_ruleset's output (uid scoping, always-allowed
nets, per-mode final rule, allowlist) without invoking nft, so it runs anywhere in
the drift-gate. nft *syntax* is validated separately with `nft -c` where the
binary exists. Loads the generator from tools/ via SourceFileLoader.

Run:  python test_mios_egress.py

<!-- mios-src:99b212f0c3bb from usr/lib/mios/agent-pipe/test_mios_egress.py:3-11 -->

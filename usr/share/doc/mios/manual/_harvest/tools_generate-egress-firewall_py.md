<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Generate the MiOS agent egress firewall (#54). Zero-trust...

Generate the MiOS agent egress firewall (#54).

Zero-trust federation calls for an OUTBOUND firewall: a compromised or misled
agent must not be able to exfiltrate to arbitrary internet hosts. The correct
layer for that is the OS (nftables), scoped to the agent's uid -- an app-level
hook would be incomplete (httpx clients are constructed ad-hoc throughout the
orchestrator). This emits that ruleset from SSOT; the operator applies it.

It is uid-scoped, so it does not disturb other users: `web_search` keeps working
because the agent reaches searxng over loopback, and searxng (a different uid)
reaches the internet.

<!-- mios-src:15b902cf01e4 from tools/generate-egress-firewall.py:3-14 -->

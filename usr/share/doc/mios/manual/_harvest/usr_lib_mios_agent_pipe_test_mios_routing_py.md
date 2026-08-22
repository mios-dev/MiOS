<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_routing (refactor R2 ROUTING-layer extraction). Pure stdlib, no server.py/DB/network/pytest. Writes a synthetic mios.toml [routing] block + points MIOS_TOML at it to exercise the real config readers (_load_routing_phrases lowercases + sorts longest-first; _load_routing_domains parses [routing.domains.*] + the router_enable switch), then drives _deterministic_action_route through the configure() DI seam (synthetic fast-path verb sets + launch fillers + compound action vocab) to prove an unambiguous "open <app>" binds open_app, a quoted "type '<text>'" binds pc_type, and a question / compound / non-trigger message routes to None. Guards the extracted layer so a later move can't silently change the deterministic pre-router contract or the SSOT phrase parsing.
AI-related: ./mios_routing.py
AI-functions: check, t_load_phrases, t_load_domains, t_deterministic_route, main

<!-- mios-src:d9bb6d8c3e1e from usr/lib/mios/agent-pipe/test_mios_routing.py:1-4 -->


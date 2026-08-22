<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_fanout (council/swarm fan-out SELECTION; de-hardcoded to model-driven relevance). Pure stdlib, no server.py/DB/network/pytest. Verifies the DETERMINISTIC parts (eligibility filter: opt-out/outage/research-gate; council-equal-weight fallback: sub-lane-diverse + endpoint dedup + cap; force_council all-eligible; council-mode cap) AND the MODEL-DRIVEN default path: _pick_fanout_agents honors the model's chosen subset, degrades OPEN to council-equal-weight when the model returns None, and _model_select parses the micro-model's JSON name array + validates names ⊆ candidates + caps (a fake httpx returns canned content -- NO real network). Proves there is no hand-coded relevance scorer left: relevance is the model's call, width is bounded by the caps.
AI-related: ./mios_fanout.py
AI-functions: check, setup, t_eligible, t_council_fallback, t_force_council, t_council_mode, t_default_model, t_default_degrade, t_model_select, main

<!-- mios-src:1d35713f4397 from usr/lib/mios/agent-pipe/test_mios_fanout.py:1-4 -->


<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_dci (refactor R6 DCI extraction). Pure stdlib, no server.py/DB/httpx-network/pytest. Pins the DCI epistemic-act vocabulary + structured-output contract the whole deliberation layer rests on: _DCI_ACTS is the 14-act 6-family table, _DCI_ACT_NAMES is its sorted key list and is also the act-enum inside _DCI_ACT_SCHEMA (required = act/content/confidence), the four persona system prompts + _persona_prompt builder are non-empty and list only their allowed acts, _PERSONA_ALLOWED_ACTS partitions the families, and configure() injects the server-side _db_*/auth helpers. One flow-control assertion drives run_dci_flow with a stubbed _dci_call_persona + injected no-op DB helpers (no network) to prove convergence/decision/dissent bookkeeping. Guards the extracted DCI layer against silent vocab/schema/flow drift.
AI-related: ./mios_dci.py
AI-functions: check, t_acts, t_schema, t_personas, t_persona_prompt, t_configure, t_flow, t_dissent_threshold_ssot, t_dissent_acts_ssot, t_act_type_emitted, t_flow_gate, main

<!-- mios-src:5455be1b53d6 from usr/lib/mios/agent-pipe/test_mios_dci.py:1-4 -->


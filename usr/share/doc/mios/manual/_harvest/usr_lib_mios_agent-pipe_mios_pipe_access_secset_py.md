<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_secset -- SSOT-derived security verb sets (WS-A14, the...

mios_secset -- SSOT-derived security verb sets (WS-A14, the AIOS Access-Manager
firewall/HITL scope layer).

Pure stdlib. The taint firewall + the HITL block gate key off a "high-privilege"
verb set; before WS-A14 that set was a hardcoded Python literal that could drift
from the SSOT [security].firewall_high_privilege_verbs list (which existed but
was never consumed). This module derives the EFFECTIVE set as
curated_base ∪ SSOT_list -- the curated base is the never-removed floor (a verb
the code knows is dangerous can't be dropped by an SSOT edit), and the SSOT can
ADD verbs without a code change. Same pattern for the always-taint verb set.

<!-- mios-src:3843966bb641 from usr/lib/mios/agent-pipe/mios_pipe/access/secset.py:3-13 -->

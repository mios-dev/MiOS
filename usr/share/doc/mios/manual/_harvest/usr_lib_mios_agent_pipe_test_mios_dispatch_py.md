<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Offline stdlib-assert test for mios_dispatch (the verb->bash dispatch chokepoint). Verifies _build_dispatch_cmd shapes a representative verb's argv (both a hardcoded branch and an SSOT cmd-template verb), that the dispatch table covers a sample of planner-emittable verbs, and that a guarded verb STAYS GATED -- a HITL-blocked verb is refused (exit 126, hitl_blocked) WITHOUT ever reaching the broker (the bounded/broker leg is stubbed to raise if called), and a tainted high-privilege verb is firewall_block'd at the inner gate before the broker. No network / no DB / no broker socket.
AI-related: ./mios_dispatch.py, ./server.py
AI-functions: (assert script)

<!-- mios-src:5efa70ddd82e from usr/lib/mios/agent-pipe/test_mios_dispatch.py:1-3 -->


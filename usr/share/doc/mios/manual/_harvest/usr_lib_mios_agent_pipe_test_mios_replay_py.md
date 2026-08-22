<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for the T-225 run-template REPLAY path -- the pure matcher (mios_pipe.routing.replay), the capture round-trip (mios_pipe.routing.run_template), and the planner branch that spends the saving. Proves the two clauses the roadmap asks for by COUNTING planner HTTP calls behind a stub client: a repeated intent returns the stored DAG with ZERO planning calls, and a fuzzy or merely-partial variant falls back to planning rather than replaying the wrong plan. Also pins the properties that make the match safe: order- and punctuation-insensitive keying, two empty token sets scoring 0.0 rather than a perfect 1.0, a row with no dag never consuming the match, and the whole path inert at the default flag.
AI-related: ./mios_pipe/routing/replay.py, ./mios_pipe/routing/run_template.py, ./mios_pipe/routing/planner.py, /usr/share/mios/mios.toml
AI-functions: check, t_keying, t_similarity, t_match, t_capture_roundtrip, t_planner_replay, main

<!-- mios-src:c6ef95376b4b from usr/lib/mios/agent-pipe/test_mios_replay.py:1-4 -->


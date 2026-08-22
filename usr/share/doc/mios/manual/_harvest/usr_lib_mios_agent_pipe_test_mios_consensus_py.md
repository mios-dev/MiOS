<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib offline unit tests for mios_pipe.routing.consensus -- the weighted multi-judge Definition-of-Done fold (CONS-01). No network / no DB / no live model: the module is pure, so every case is a direct call. Proves the Done-When math -- conflicting judges resolve by weighted vote rather than majority-by-count, an abstaining lane is dropped from both sides instead of counting as "no", a sub-quorum panel returns decision=None so the caller keeps its single-judge answer, reliability weights clamp at the floor, and RRF ranks a candidate two lanes agree on above one lane's favourite. Run: python test_mios_consensus.py
AI-related: ./mios_pipe/routing/consensus.py, ./mios_pipe/routing/reflect.py
AI-functions: main

<!-- mios-src:95fc1635892f from usr/lib/mios/agent-pipe/test_mios_consensus.py:1-3 -->


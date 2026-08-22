<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure consensus math for multi-judge Definition-of-Done verdicts. weighted_vote folds 2-3 independent judge lanes' yes/no/abstain verdicts into one reliability-weighted decision; reciprocal_rank_fusion merges the lanes' ranked candidate lists (standard RRF, score = sum w/(k+rank)); resolve_weights turns a reliability mapping into per-lane weights and degrades to uniform when no reliability signal exists. No I/O, no config import, no server import -- the caller supplies lanes, verdicts and weights, so every branch is isolation-testable.
AI-related: ./reflect.py, ../../test_mios_consensus.py, usr/share/mios/mios.toml [consensus]
AI-functions: resolve_weights, weighted_vote, reciprocal_rank_fusion, quorum_reached

<!-- mios-src:234e875052f9 from usr/lib/mios/agent-pipe/mios_pipe/routing/consensus.py:1-3 -->


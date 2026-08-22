<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Provides filesystem-safe KV-cache fork primitives for the agent-pipe, enabling branching of shared conversation prefixes into independent child KV files via a two-step save/restore plan to support multi-path reasoning.
AI-related: mios-kv
AI-functions: kv_filename, conv_token, validate_fork, plan_fork, fork_outcome, parse_bool, clamp_branches

<!-- mios-src:612682703b1e from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:1-3 -->


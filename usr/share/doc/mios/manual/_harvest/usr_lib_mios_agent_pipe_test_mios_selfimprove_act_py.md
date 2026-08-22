<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Standalone unit test for mios_selfimprove_act (T-062 ACT + T-064 proof-of-utility decision core): structural anti-reward-hacking isolation (improvable allowed / protected denied / deny-wins / empty-degrade-closed), proposal shape validation, the Autodata solver-gap discriminative signal + eval curation, the pass^k reliability score, the proof-of-utility non-regression gate (margin + require-improvement), and decide_proposal composing them so a proposal targeting the protected evaluator surface is rejected BEFORE it is ever scored. Pure stdlib + the two sibling modules (mios_selfimprove_act / mios_bench) -- no server.py / DB / live models. Surfaces/ids are synthetic non-dictionary tokens so the test proves STRUCTURAL set-membership, never an English/keyword match.
AI-related: mios_selfimprove_act, mios_bench
AI-functions: _check, t_isolation, t_validate, t_gap, t_curate, t_passhatk, t_proof, t_decide, main

<!-- mios-src:b185dc25e055 from usr/lib/mios/agent-pipe/test_mios_selfimprove_act.py:1-3 -->


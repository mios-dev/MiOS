<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_selfimprove_act (T-062/T-064...

Standalone unit test for mios_selfimprove_act (T-062/T-064 ACT decision core).

Pure stdlib + the sibling modules only -- no server.py / DB / live models. Proves
the ACT half (a) STRUCTURALLY isolates the evaluator/eval/lane-config from a
proposal (anti-reward-hacking), (b) curates eval tasks by the solver-gap, and
(c) accepts a proposal ONLY when it does not regress the baseline (pass^k), with
isolation enforced before any score is consulted.

Synthetic, non-dictionary surface/id tokens throughout: the improvable/protected
sets are made-up kinds the test supplies, so a PASS proves structural set
membership rather than any baked-in English vocabulary.

Run:  python test_mios_selfimprove_act.py

<!-- mios-src:08af0d0c0828 from usr/lib/mios/agent-pipe/test_mios_selfimprove_act.py:3-16 -->

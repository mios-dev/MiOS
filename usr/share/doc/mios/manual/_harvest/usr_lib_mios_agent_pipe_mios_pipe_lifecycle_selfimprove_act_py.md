<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure self-improvement ACT-half decision core (T-062 ACT + T-064 proof-of-utility). The OBSERVE half (mios_selfimprove.analyze) surfaces WHAT to improve; this turns a finding into a bounded, VALIDATED change PROPOSAL and decides whether it may be QUEUED -- it never applies anything. Three composed, stdlib+mios_bench-only decisions: (1) STRUCTURAL anti-reward-hacking isolation (proposal_target_allowed/validate_proposal) -- a proposal may ONLY target a kind in the SSOT improvable surface and NEVER one in the SSOT protected surface (the evaluator/eval-data/lane-config); deny wins, so a proposal that tries to edit the thing that judges it is rejected BEFORE it is ever scored (the Autodata reward-hacking lesson); (2) the Autodata solver-GAP discriminative signal (solver_gap/is_discriminative/curate_eval) -- a held-out eval task carries signal only when a strong solver beats a weak one by >= the SSOT gap, so trivial/impossible tasks are dropped; (3) proof-of-utility (pass_hat_k_score over mios_bench + proof_of_utility) -- accept a proposal ONLY IF its pass^k does not regress the baseline beyond the SSOT margin (and, where required, strictly improves). decide_proposal composes all three into ONE verdict. Pure functions over plain dicts/numbers: no DB, no server import, no model call, no I/O -> unit-testable (test_mios_selfimprove_act.py). The orchestration that drafts proposals (a model call), runs the solver lanes, and writes the QUEUE lives in mios_daemons (the loop), default-off; this module only DECIDES. Every threshold/flag/surface is a parameter supplied by the caller from the [selfimprove] SSOT -- nothing numeric or lexical is baked here.
AI-related: ./mios_selfimprove.py, ./mios_bench.py, ./mios_daemons.py, ./test_mios_selfimprove_act.py, /usr/share/mios/mios.toml
AI-functions: proposal_target_allowed, validate_proposal, solver_gap, is_discriminative, curate_eval, pass_hat_k_score, proof_of_utility, decide_proposal

<!-- mios-src:8e6f3095b3b7 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:1-3 -->


<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure, DB-free scoring core for the MiOS agentic-capability benchmark harness. Implements pass@k (unbiased "at least one of k succeeds", OpenAI/Codex) and tau-bench pass^k ("all k succeed"), plus the CLASSic rollup (Cost/Latency/Accuracy/Stability/Security) over trial records. Stdlib-only; the libexec mios-bench CLI runs live trials on the `agent_pipe` port.
AI-related: ./mios_quota.py, ./mios_trace.py, ./mios_stress.py, /usr/libexec/mios/mios-bench, ./test_mios_bench.py, ../../../share/doc/mios/concepts/aios-engineering-blueprint.md
AI-functions: comb_ratio, pass_at_k, pass_hat_k, iid_pass_hat_k, aggregate_pass_at_k, aggregate_pass_hat_k, aggregate_pass_and_k_rate, percentile, classic_rollup

<!-- mios-src:9fb08b56a137 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/bench.py:1-3 -->


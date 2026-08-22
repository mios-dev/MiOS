<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_bench -- pure scoring core for the MiOS...

mios_bench -- pure scoring core for the MiOS capability-benchmark harness.

The AIOS engineering blueprint flagged the single clearest external-validation
gap: MiOS instruments the *operational* CLASSic dimensions (cost/latency/
stability/security via mios_quota / mios_trace / mios_stress / the fitness gates)
but had NO standard agentic-capability benchmark runner. This module is the pure,
deterministic half of that harness: the reliability metrics + the CLASSic rollup.
The libexec `mios-bench` CLI drives trials against the agent-pipe endpoint
(:8640) -- that half needs the live VM -- then scores the results through here.

RESEARCH GROUNDING (web-verified):
  * pass@k -- "at least one of k samples passes". Unbiased estimator
    (OpenAI Codex / HumanEval): 1 - C(n-c, k) / C(n, k) for n samples, c correct.
  * pass^k -- tau-bench's worst-case RELIABILITY metric, "ALL k attempts
    succeed" (arXiv 2406.12045). Unbiased estimator: C(c, k) / C(n, k). The i.i.d.
    closed form is p^k (a 93%-pass@1 agent is only ~0.93^8 ~= 0.56 reliable at
    k=8) -- consistency, not average, is what production needs.
  * CLASSic (arXiv 2511.14136 / Aisera) -- Cost, Latency, Accuracy, Stability,
    Security: production agent quality is multi-dimensional, not just accuracy.

<!-- mios-src:42187aaa7ab6 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/bench.py:3-22 -->

### Fraction of tasks that CLEAR the HARD pass^k gate -- the...

Fraction of tasks that CLEAR the HARD pass^k gate -- the suite-wide analogue
    of the mios-skills promotion gate. That gate demands ALL k repeats succeed, so
    a task clears iff its pass^k reliability is a perfect 1.0 (every trial passed ->
    any k-subset all-succeeds; pass_hat_k(n,c,k)==1 iff c==n). This is DISTINCT from
    the MEAN pass^k (aggregate_pass_hat_k): the mean averages partial reliabilities,
    this counts how many tasks would survive the all-or-nothing gate. Reuses
    pass_hat_k. Tasks with fewer than k trials are skipped. 0.0 if none qualify.

<!-- mios-src:f313cd7fa8e2 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/bench.py:83-89 -->

### Roll a flat list of per-trial records into the CLASSic...

Roll a flat list of per-trial records into the CLASSic dimensions. Each
    record: {task: str, ok: bool, cost: float, latency_ms: float,
    error: bool, security_violation: bool}. Returns:

      cost_total / cost_mean        -- sum + mean of `cost` (Cost)
      latency_p50 / latency_p95     -- ms percentiles of `latency_ms` (Latency)
      accuracy                      -- fraction ok (Accuracy)
      stability                     -- mean pass^k across tasks grouped by `task`
                                       (worst-case reliability, NOT average); falls
                                       back to (1 - error_rate) if k<=1 (Stability)
      security                      -- 1 - fraction with security_violation (Security)
      n / n_tasks                   -- trial + distinct-task counts

    Pure + deterministic; the CLI passes the trial log straight in.

<!-- mios-src:ebf3c28e2367 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/bench.py:113-126 -->

<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_bench (agentic-capability benchmark scoring core). Pure stdlib, no server.py/DB/pytest. Verifies the unbiased pass@k estimator (pass@1=c/n, all-correct->1, c==0->0, k>n->0, monotonic in k), tau-bench's pass^k ("all k succeed": pass^1=c/n, c==n->1, c<k->0, pass^k<=pass@1<=pass@k) incl. the exact combinatorial value C(c,k)/C(n,k), the i.i.d. p**k closed form (the ~56%-at-k=8 reliability intuition), aggregate skip-when-n<k, percentile linear interpolation, and the CLASSic rollup (cost/latency-percentiles/accuracy/stability/security + task grouping).
AI-related: ./mios_bench.py
AI-functions: check, main

<!-- mios-src:5705199a92a9 from usr/lib/mios/agent-pipe/test_mios_bench.py:1-4 -->


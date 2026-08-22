<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Pure Jensen-Shannon divergence monitor over agent-plane verdict/intent/score histograms (CONS-02). histogram() folds raw label samples into a normalized distribution; jensen_shannon() returns the bounded (0..1, log base 2) divergence between a live window and a frozen baseline; compare() scores every named axis at once and reports which ones crossed the alert threshold. The Goodhart early-warning alarm: self-improvement and multi-judge consensus can quietly optimize the verdict distribution, and without a divergence measure that shift is invisible until behaviour visibly degrades. No I/O, no config import, no DB, no server import -- the caller supplies the samples and the baseline.
AI-related: ../routing/consensus.py, ../../server.py, ../../test_mios_drift.py, usr/share/mios/postgres/schema-init.sql, usr/share/mios/mios.toml [drift_monitor]
AI-functions: histogram, jensen_shannon, compare, is_alerting

<!-- mios-src:89662a2c8eba from usr/lib/mios/agent-pipe/mios_pipe/observability/drift_monitor.py:1-3 -->


<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Guards the T-230 syscall filter...

!/usr/bin/env bash
AI-hint: Guards the T-230 syscall filter on usr/libexec/mios/mios-sandbox-exec. Two tiers: a generator tier that always runs (the filter builds, an unsupported architecture is REFUSED rather than silently unfiltered, and the SSOT list extends the baseline floor), and a live tier under a real bwrap that proves the thing the roadmap asked for -- the confined process reports a loaded filter instead of `Seccomp: 0`, a denied syscall returns EPERM instead of succeeding, ordinary work still runs, and the filesystem/network jail still holds. Also asserts the refusal stance: with the generator unavailable, level=enforce must EXIT rather than run a verb with no filter.
AI-related: usr/libexec/mios/mios-sandbox-exec, usr/libexec/mios/mios-seccomp-filter, usr/lib/mios/agent-pipe/mios_pipe/access/seccomp.py, usr/share/mios/mios.toml
AI-functions: log, die, ok, run_confined

<!-- mios-src:f3270e1c9aa3 from tests/test-sandbox-seccomp.sh:1-4 -->


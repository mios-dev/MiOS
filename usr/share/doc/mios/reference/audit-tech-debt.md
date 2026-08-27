<!-- AI-hint: Measured refresh of the MiOS tech-debt map (ADR-0011 territory) -- server.py split-seam manifest, kill-eval status, shellcheck warning-ratchet upgrade, compiled-template + Law-14 language-policy status, with a drop-in module-size gate and declining-baseline shellcheck ratchet. -->
<!-- AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_dispatch.py, usr/lib/mios/agent-pipe/mios_template.py, automation/lint-shell.sh, automation/98-drift-checks.sh, usr/share/mios/mios.toml, .github/workflows/mios-ci.yml -->

# MiOS Tech-Debt Map — Measured Refresh (2026-07-31)

## Overview

This is a **measured** refresh of the ADR-0011 tech-debt map. Every claim below was
verified against the working tree at `C:\MiOS` (the git root). The headline finding:
**most of the ADR-0011 debt map has already been executed.** The stale assertions
carried in memory (server.py ~26k then ~9k; 3× `mios.toml` at conflicting versions;
9 eval-on-agent-args verbs; "no shellcheck CI"; "add a compiled-template system";
"define a language policy") are, one after another, **already resolved or already
codified as law.** What remains is a *narrower, concrete* set of items — chiefly the
`server.py` composition-root split and one genuinely-missing fitness function

*Audit completed and reconciled against SSOT.*

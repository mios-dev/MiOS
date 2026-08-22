<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: SSOT-render conformance lint -- asserts every ${MIOS_*} placeholder referenced in a Quadlet Exec=/Environment= line has BOTH a typed export/mapping in tools/lib/userenv.sh AND an allowlist entry in automation/34-render-quadlets.sh, so no placeholder silently relies only on its inline shell default (a dead key). Runs standalone or as a build sub-phase; pure bash + grep, no python deps.
AI-related: ./tools/lib/userenv.sh, ./automation/34-render-quadlets.sh, ./usr/share/containers/systemd, /usr/share/mios/mios.toml
AI-functions: _norm_refs, _in_userenv, _in_render, main
automation/97-ssot-lint.sh
----------------------------------------------------------------------------
THE META-FIX (W0-T1). The render pipeline (34-render-quadlets.sh) bakes
${MIOS_*:-default} placeholders in the Quadlet *.container files with the
values resolved from mios.toml by userenv.sh. For that flow to actually
carry an operator's mios.toml value through to a running container, a
placeholder MUST be wired on BOTH ends:

  (a) tools/lib/userenv.sh         -- a typed slot ("section.field","MIOS_X")
                                      (or an explicit export) that EMITS the
                                      MIOS_X env var from mios.toml; AND
  (b) automation/34-render-quadlets.sh -- an allowlist entry (the envsubst
                                      '${MIOS_X}' list AND/OR the bash-
                                      fallback `for var in ...` list) so the
                                      renderer actually substitutes MIOS_X.

A placeholder wired on neither (or only one) end is a DEAD KEY: at render
time it silently collapses to its inline `:-default`, so editing mios.toml
does nothing and the value is un-tunable. This lint walks every Quadlet
Exec=/Environment= line, pulls each referenced ${MIOS_*}, and asserts the
two-sided wiring. It retroactively catches the known dead keys
(MIOS_SGLANG_TOOL_PARSER, MIOS_PORT_CPU_NODE, MIOS_CPU_NODE_THREADS, ...).

Default behaviour: emit a per-key error for every orphan and exit 1 if any
orphan is found (so it can fail a CI/build step). It NEVER mutates anything
-- read-only static analysis. Set MIOS_SSOT_LINT_SOFT=1 to report orphans
but still exit 0 (advisory mode, e.g. while a fix is staged).

Usage:
  automation/97-ssot-lint.sh              # lint, exit 1 on any orphan
  MIOS_SSOT_LINT_SOFT=1 automation/97-ssot-lint.sh   # advisory (exit 0)
  MIOS_SSOT_LINT_ROOT=/path automation/97-ssot-lint.sh  # override repo root

User-agnostic: no User=/uid assumptions, no network, no python.
----------------------------------------------------------------------------

<!-- mios-src:9754d3acf372 from automation/97-ssot-lint.sh:1-40 -->


<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for the [units]...

!/usr/bin/env python3
AI-hint: Drift gate for the [units] projection debt register. The authoritative rendering comparison lives in the Rust test tools/native/mios-unit-gen/tests/projection.rs, which CI always runs; this gate enforces the half that needs no toolchain -- the register names real, declared, sorted, unique units and never grows past [unit_projection].max_drift. It runs mios-unit-gen --check too when a built binary is there, and SAYS SO when there is not, because a gate that skips quietly is how the golden test stayed green over a copy of itself for months.
AI-related: usr/share/mios/mios.toml, tools/test_check-unit-projection.py, tools/native/mios-unit-gen/src/lib.rs, tools/native/mios-unit-gen/tests/projection.rs, automation/98-drift-checks.sh
AI-functions: declared_units, unit_aliases, _built, register, max_drift, shipped, hygiene, binary_path, run_binary, main

<!-- mios-src:8221f2197afe from tools/check-unit-projection.py:1-4 -->


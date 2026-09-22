<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Documentation-plane drift...

!/usr/bin/env python3
AI-hint: Documentation-plane drift gates in one module: ratchet monotonicity, manual links, comment-lexer equivalence, header comment syntax, generated prose in resolvers, redaction coverage. The subcommand selects the gate.
AI-doc: usr/share/doc/mios/manual/tools.md

<!-- mios-src:5fb9ee5e307d from tools/check-docs.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Runtime and unit gates in...

!/usr/bin/env python3
AI-hint: Runtime and unit gates in one module: container names, privileged Quadlets, service URLs, daemon governor coverage, firstboot degrade-open, firstboot provisioners, artifact verification and resolver twin equivalence. The subcommand selects the gate.
AI-doc: usr/share/doc/mios/manual/tools.md
AI-related: tools/verify-images.py, usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh

<!-- mios-src:a92031b05e0e from tools/check-runtime.py:1-4 -->

### !/usr/bin/env python3 AI-hint: SSOT-plane drift gates in...

!/usr/bin/env python3
AI-hint: SSOT-plane drift gates in one module: mios.toml integrity, consumer keys, unit projection, port fallbacks and binding, variant registry, deploy formats, role SSOT, node pool, blade coverage and fleet safety. The subcommand selects the gate.
AI-doc: usr/share/doc/mios/manual/tools.md

<!-- mios-src:35c17a4f275b from tools/check-ssot.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Task-plane drift gates in...

!/usr/bin/env python3
AI-hint: Task-plane drift gates in one module: TASKS.md table-vs-section parity, AGY task schema, and AGY id/dependency resolution. The subcommand selects the gate.
AI-doc: usr/share/doc/mios/manual/tools.md
AI-functions: main, status_parity_main, schema_main, agy_main

<!-- mios-src:1936f5115024 from tools/check-tasks.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Test-and-fixture hygiene...

!/usr/bin/env python3
AI-hint: Test-and-fixture hygiene gates in one module: leaked fixtures, temp fixture cleanup, negative-test registration, Rust test coverage, schema consumers, tracked-file readability and module length. The subcommand selects the gate.
AI-doc: usr/share/doc/mios/manual/tools.md

<!-- mios-src:63c4b6542781 from tools/check-testhygiene.py:1-3 -->

### !/usr/bin/env python3 AI-hint: The three largest drift...

!/usr/bin/env python3
AI-hint: The three largest drift checks, lifted out of their shell heredocs so they can be imported, linted and tested.
AI-related: mios_manifest, mios_capreg, mios_surface, mios_comments, /usr/libexec/mios/mios-resolver, /usr/share/mios/mios.toml, mios-resolver, mios-env-snapshot, mios-drift-ctx-test, mios-bootstrap
AI-functions: check_resolver_differential_parity, check_legibility_ratchet, lines, _is_generated, check_no_inert_ssot_tables, check_no_duplicate_value_key, emit, esc, unesc, _shape, check_unwired_modules

<!-- mios-src:184feb71654c from tools/drift-checks.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Lists tracked files for a...

!/usr/bin/env python3
AI-hint: Lists tracked files for a gate, raising when git could not answer -- an empty listing is never reported as a clean corpus.
AI-related: tools/check-testhygiene.py, tools/check-docs.py, tools/check-ssot.py, tools/sync-bootstrap.py
AI-functions: tracked

<!-- mios-src:5f0c8b51ae6a from tools/mios_tracked.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Asserts a generator's...

!/usr/bin/env python3
AI-hint: Asserts a generator's --check mode compares what its write mode produces; the pairs are read from the gate's own projection-evidence emitter, not listed here.
AI-related: tools/generate-bib-configs.py, tools/generate-gate-index.py, automation/98-drift-checks.sh

<!-- mios-src:075d56151287 from tools/test_generator_check_agrees_with_write.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Fixtures for...

!/usr/bin/env python3
AI-hint: Fixtures for render-desktop.py -- proves the launcher renderer derives its port from SSOT, refuses an empty launcher table, and flags a .desktop file no [desktop.launchers] entry declares.
AI-related: tools/render-desktop.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
AI-functions: main

<!-- mios-src:55e7e1836ee4 from tools/test_render-desktop.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Fixtures for...

!/usr/bin/env python3
AI-hint: Fixtures for sync-bootstrap.py -- the Law 15 mirror. Proves it reports drift without --apply, that a table mirror rewrites values rather than appending duplicates, and that it never touches a surface the manifest does not declare.
AI-related: tools/sync-bootstrap.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
AI-functions: main

<!-- mios-src:b2ff609b2b64 from tools/test_sync-bootstrap.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Verifies the built...

!/usr/bin/env python3
AI-hint: Verifies the built deployment artifacts against the SSOT format matrix; an empty or partial build tree is a failure that names the formats that produced nothing.
AI-related: usr/share/mios/mios.toml, Justfile, tools/check-runtime.py

<!-- mios-src:0933f257ef38 from tools/verify-images.py:1-3 -->

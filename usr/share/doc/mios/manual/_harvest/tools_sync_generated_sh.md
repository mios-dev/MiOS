<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: One entry point that...

!/usr/bin/env bash
AI-hint: One entry point that regenerates EVERY SSOT projection in dependency order (ports -> globals -> quadlets -> names -> env-baseline -> AI manifests), so a contributor cannot land a change with a stale generated artefact.
AI-related: tools/render-ports.py, tools/render-globals.py, tools/generate-pod-quadlets.py, tools/generate-names-registry.py, tools/generate-ai-manifest.py, automation/98-drift-checks.sh
AI-functions: _register_new_files, main

ORDER MATTERS and is the whole point of this script:
  1. render-ports        [ports.categories] -> flat [ports] + ${MIOS_PORT_*:-N} fallbacks
  2. render-globals      mios.toml -> automation/lib/globals.{sh,ps1}
  3. pod-quadlets        mios.toml -> usr/share/containers/systemd/*
  4. names-registry      -> referenced_names.txt + names.generated.txt
  5. env-baseline        MUST run after 1-4, under a CLEAN env: a login shell
                         sources /etc/profile.d/mios-env.sh and leaks the
                         host's MIOS_* exports into the snapshot, which then
                         can never match a CI regeneration.
  6. AI manifests        they embed the CONTENT of automation/ and tools/,
                         so every step above invalidates them.
  7. manual ledger       LAST -- a census of comment blocks across every
                         tracked source file, so everything above moves it.

<!-- mios-src:ed1bc1429de5 from tools/sync-generated.sh:1-18 -->


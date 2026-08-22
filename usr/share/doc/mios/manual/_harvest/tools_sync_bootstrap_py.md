<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Law 15 repo sync. Mirrors...

!/usr/bin/env python3
AI-hint: Law 15 repo sync. Mirrors the surfaces mios.toml [bootstrap.sync] declares from mios.git into mios-bootstrap.git, and mirrors the SSOT tables it names into bootstrap's root mios.toml. --check is the drift gate; --apply is what CI runs after a green build so the two repos cannot drift between releases.
AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh, installation/UNIFY.md, .github/workflows/mios-ci.yml
AI-functions: load_manifest, mirror_files, mirror_tables, main

<!-- mios-src:1eca232c6c39 from tools/sync-bootstrap.py:1-4 -->


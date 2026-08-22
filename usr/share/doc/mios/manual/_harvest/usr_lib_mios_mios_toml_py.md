<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: The single shared Python resolver for the layered mios.toml SSOT -- the Python peer of tools/lib/userenv.sh. Collapses the ~13 independently re-rolled `try: import tomllib except: import tomli` + `deep_merge` + hardcoded-layer-path copies scattered across usr/libexec/mios/* and the agent-pipe tree into ONE overlay implementation with ONE set of semantics (vendor < host < user, highest wins, empty strings do not override). load_merged() gives the full three-layer overlay; load_vendor() gives the vendor-only view the offline drift-gates intentionally read; colors() is the ONE canonical palette-default map (mirrors mios.toml [colors]) so no tool re-declares the 12 hexes. Importers add usr/lib/mios to sys.path and `import mios_toml`. Pairs with mios-theme-render + mios-sync-theme (palette projection) and the drift-gates.
AI-related: ../../libexec/mios/mios-theme-render, ../../libexec/mios/mios-sync-theme, ../../share/mios/mios.toml, ../../../tools/lib/userenv.sh, ../../../automation/98-drift-checks.sh
AI-functions: load_merged, load_vendor, deep_merge, section, get, colors, layer_paths

<!-- mios-src:14ded38fe3a0 from usr/lib/mios/mios_toml.py:1-3 -->


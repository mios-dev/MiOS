<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### validate-kargs.py -- 'MiOS' kargs.d schema validator....

validate-kargs.py -- 'MiOS' kargs.d schema validator.

Checks every *.toml in:
  kargs.d/                              (repo root drop-ins)
  usr/lib/bootc/kargs.d/  (image-baked drop-ins)

Schema rules (bootc-dev/bootc authoritative):
  - Top-level key `kargs` (required) must be a list of strings.
  - Top-level key `match-architectures` (optional) must be a list of strings.
  - NO other top-level keys.
  - NO [section] table headers anywhere in the file.
  - Each kargs entry must be a single string (not space-joined multi-arg).
  - Keys with "delete" in their name are invalid parameter -- reject.

Exit codes: 0 = pass, 1 = validation failure(s), 2 = usage error.

<!-- mios-src:ad7c112407e8 from automation/validate-kargs.py:3-19 -->

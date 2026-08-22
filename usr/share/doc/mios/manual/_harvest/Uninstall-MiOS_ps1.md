<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Dry-run (default) -- see exactly what would be removed:

Dry-run (default) -- see exactly what would be removed:

<!-- mios-src:86a2cb8a5014 from Uninstall-MiOS.ps1:33-33 -->

### File at data-drive root. DO NOT blanket-delete every...

File at data-drive root. DO NOT blanket-delete every non-KEEP
file -- that nukes genuine operator data dropped at M:\ root.
Only remove files matching a known MiOS artifact pattern;
preserve anything else (whitelist parity with $MIOS_DIRS).

<!-- mios-src:6ed6649c6d3d from Uninstall-MiOS.ps1:192-195 -->

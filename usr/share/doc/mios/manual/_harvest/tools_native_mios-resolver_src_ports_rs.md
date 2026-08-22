<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Allocate every `[ports]` value from `[ports.categories]`...

Allocate every `[ports]` value from `[ports.categories]`, in place.

Must run AFTER all layers merge so a factory/OEM default in the vendor
mios.toml, an operator override in /etc/mios/mios.toml, and a user override
in ~/.config all feed the same derivation. `members` is ordered and the order
IS the numbering, so adding or removing a service reallocates the category
without a hand edit. `pinned` entries are protocol contracts (DNS/53) and are
written verbatim.

This OVERRIDES the flat `[ports]` table, which is only a rendered projection
kept for readability -- otherwise a stale vendor literal would silently beat
an operator who retargeted a category base.

<!-- mios-src:43bce08392de from tools/native/mios-resolver/src/ports.rs:5-16 -->

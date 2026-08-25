<!-- AI-hint: Reference page for the port allocation table and the numbered Architectural Laws. The tables between MIOS-GEN markers are DERIVED from mios.toml by `mios-manual render`; the prose around them is authored and is never rewritten.
     AI-related: usr/share/mios/mios.toml, usr/libexec/mios/mios-manual, tools/render-ports.py, automation/98-drift-checks.sh -->
# Ports and Laws

This page has two kinds of content, and the difference matters if you edit it.

Everything **between** a `MIOS-GEN` marker pair is derived from `mios.toml` and is
rewritten in full by `mios-manual render`. Do not hand-edit inside a pair; change the
SSOT and re-render. Everything **outside** the pairs is authored prose, and `render`
has no code path that can write there.

## Port allocation

Ports are not hand-assigned. Each category in `[ports.categories]` declares a `base` and a
`stride`, and a member's port is derived from its position in the ordered member list.
Adding a service allocates the next port in its band; moving a category's `base` moves the
whole band. A `pinned` entry opts a protocol-fixed port out of that arithmetic -- DNS on 53
is the obvious case, since it cannot float.

<!-- MIOS-GEN:ports -->
| Category | Service | Port |
|---|---|---|

<!-- derived from usr/share/mios/mios.toml [ports.categories] -->
<!-- /MIOS-GEN:ports -->

## Architectural Laws

The laws are invariants, not guidelines: each one names the check that enforces it, and a
failing law fails the build. The `id` column is the numbering SSOT -- `mios.toml [laws]` --
so a law's number is stable even as the registry grows.

<!-- MIOS-GEN:laws -->
| # | Law | Applies to | Enforced by |
|---|---|---|---|

<!-- derived from usr/share/mios/mios.toml [laws].laws -->
<!-- /MIOS-GEN:laws -->

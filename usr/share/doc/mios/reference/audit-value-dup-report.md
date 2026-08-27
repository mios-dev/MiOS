<!-- AI-hint: Measured MIOS_* value-duplication audit feeding the AGY de-dup campaign (AGY-856..930); groups the 2416 resolver-emitted env vars by VALUE, classifies every >=2-key group {true-alias | distinct-configurable-fact | intentional-many-to-one | unset-default}, quantifies 13 systematic prefix-alias families (408 keys), and lists cross-surface hardcoded literals that duplicate SSOT values. Regenerate via usr/libexec/mios/mios-env-snapshot. -->
<!-- AI-related: usr/libexec/mios/mios-env-snapshot, usr/lib/mios/userenv.sh, usr/share/mios/mios.toml, usr/share/mios/configurator/mios.html, usr/share/mios/knowledge/mios-knowledge-graph.json, MiOS-SBOM.csv, usr/share/doc/mios/reference/audit-value-dup-report.md -->

# MiOS Value-Duplication Audit (AGY-856..930 feed)

**Date:** 2026-07-31 · **Source:** Resolver snapshot (`usr/libexec/mios/mios-env-snapshot`)

## Summary & Taxonomy
- Namespace analysis over 2416 `MIOS_*` environment keys resolved from `usr/share/mios/mios.toml`.
- Categorization into `true-alias`, `distinct-configurable-fact`, `intentional-many-to-one`, and `unset-default`.
- De-duplication roadmap tracked across AGY-856 through AGY-930 with strict prefix-alias invariants.

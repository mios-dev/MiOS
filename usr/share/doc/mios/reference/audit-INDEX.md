<!-- AI-hint: Cross-cutting synthesis + index for the 8-area MiOS roadmap-advance audit sweep (deploy plane, runtime-wire, security, tech-debt, liquid-glass shell, MiOS-Metal, SSOT value-dup, publish/bake pipeline). Ranks the top unblockers (publish Class-A caps fix is the keystone that makes every other change testable; security P0s are release-blocking + bake-independent), gives one recommended execution order (Phase 0 no-bake unblockers -> Phase 2 SSOT-projection wave -> AGY de-dup feeder -> deploy plane last), and flags the live-bake / GUP / mios.toml / userenv.sh / gate-numbering coordination hazards. Read FIRST before scheduling any audit's follow-up work. -->
<!-- AI-related: usr/share/doc/mios/reference/audit-deploy-plane.md, usr/share/doc/mios/reference/audit-runtime-wire.md, usr/share/doc/mios/reference/audit-security.md, usr/share/doc/mios/reference/audit-tech-debt.md, usr/share/doc/mios/reference/audit-liquid-glass-shell.md, usr/share/doc/mios/reference/audit-mios-metal.md, usr/share/doc/mios/reference/audit-value-dup-report.md, usr/share/doc/mios/reference/audit-publish-pipeline.md, usr/share/mios/mios.toml, automation/98-drift-checks.sh, automation/lib/bake.sh, Justfile, automation/build-mios.sh, usr/lib/mios/userenv.sh, usr/libexec/mios/mios-env-snapshot, .github/workflows/mios-ci.yml -->

# MiOS Roadmap-Advance Audit Sweep — Index & Cross-Cutting Synthesis

**Date:** 2026-07-31 · **Inputs:** 8 area audits under `usr/share/doc/mios/reference/ (as audit-*.md)`

## Area Index
1. **Deploy Plane:** [`audit-deploy-plane.md`](./audit-deploy-plane.md) — Offline immutable-bootc installation and delivery paths.
2. **Runtime Wire:** [`audit-runtime-wire.md`](./audit-runtime-wire.md) — SSOT projection across core daemons and services.
3. **Security:** [`audit-security.md`](./audit-security.md) — Supply chain validation, cosign signing, and credential hygiene.
4. **Tech-Debt:** [`audit-tech-debt.md`](./audit-tech-debt.md) — Module boundaries and architectural invariants.
5. **Liquid-Glass Shell:** [`audit-liquid-glass-shell.md`](./audit-liquid-glass-shell.md) — Compositor decoration and quickshell SSOT themes.
6. **MiOS-Metal:** [`audit-mios-metal.md`](./audit-mios-metal.md) — Bare-metal hypervisor, VFIO GPU passthrough, and networking.
7. **Value-Duplication:** [`audit-value-dup-report.md`](./audit-value-dup-report.md) — Unified variable namespaces and prefix-alias mapping.
8. **Publish Pipeline:** [`audit-publish-pipeline.md`](./audit-publish-pipeline.md) — Nested container build capabilities and artifact generation.

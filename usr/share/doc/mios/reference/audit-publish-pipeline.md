<!-- AI-hint: Robustness audit of the MiOS publish/bake pipeline (GitHub + Forgejo -> ghcr.io/mios-dev/mios:latest); catalogs every at-risk bare `podman build` (nested-caps exit-125 class) and every `x=$(cmd on missing-file)` under set -e (exit-1 class), a resumable-checkpointed-layers plan, firstboot-tier robustness, and a drop-in build_image_with_retry+caps helper. -->
<!-- AI-related: .github/workflows/mios-ci.yml, .forgejo/workflows/build-mios.yml, Justfile, Containerfile, automation/build.sh, automation/build-mios.sh, automation/54-bake-coderun-sandbox.sh, automation/56-fonts.sh, automation/85-bake-plan.sh, usr/libexec/mios/57-mios-sys-build.sh, usr/libexec/mios/mios-bake-group, usr/libexec/mios/mios-ai-firstboot, tools/generate-bake-plan.py, automation/98-drift-checks.sh, usr/share/mios/mios.toml, usr/share/doc/mios/reference/nested-podman-caps.md -->

# MiOS Publish/Bake Pipeline Robustness Audit

**Goal:** reliably publish `ghcr.io/mios-dev/mios:latest`.
**Date:** 2026-07-31.
**Scope:** the two build-failure classes just fixed on 0.3.0 (nested-podman caps `exit 125`; `set -e` command-substitution on a missing file `exit 1`), swept across every `automation/*.sh` bake script + the host/CI build entrypoints; plus a resumable-layers plan, firstboot-tier robustness, and a reusable drop-in helper.

---

## 0. How the publish actually works (grounded map)

| Publisher | Entrypoint | Nested-podman caps present? | Bakes bound images? |
|---|---|---|---|

*Audit completed and reconciled against SSOT.*

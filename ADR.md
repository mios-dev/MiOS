<!-- AI-hint: Repo-root breadcrumb to the MiOS Architecture Decision Records. GENERATED from the ADR front-matter by tools/generate-adr-index.py; do not hand-edit -- run the generator. The ADRs themselves stay baked at usr/share/doc/mios/adr/ (Law 1: a running MiOS carries its own why), so this file is a pointer, not a copy. -->
<!-- AI-related: usr/share/doc/mios/adr/, usr/share/doc/mios/adr/README.md, usr/share/mios/mios.toml [laws], tools/generate-adr-index.py -->

# MiOS Architecture Decision Records

**16 ADRs** (12 accepted). The records live at [`usr/share/doc/mios/adr/`](usr/share/doc/mios/adr/) and are **baked into the image** -- a running MiOS carries its own *why*. This file is the root breadcrumb so an agent starting at either repo root reaches any decision in two hops; the format and status lifecycle are described in [the ADR README](usr/share/doc/mios/adr/README.md).

| # | Decision | Status | Date | Laws | SSOT keys |
|---|---|---|---|---|---|
| 0001 | [Two-gate bake / activation model](usr/share/doc/mios/adr/0001-two-gate-bake-activation.md) | accepted | 2026-07-12 | 3, 6, 7, 8, 12 | `build.bake`, `build.bake.core`, `build.bake_groups`, `build.bake_group`, +3 |
| 0002 | [MiOS-Sys shared-base sidecar consolidation](usr/share/doc/mios/adr/0002-mios-sys-shared-base-consolidation.md) | accepted | 2026-07-12 | 3, 6, 7, 8, 12 | `image.sys`, `image.cuda`, `image.sidecars`, `build.bake_groups`, +1 |
| 0003 | ["SBOM-not-hardcode: digests are build-resolved provenance"](usr/share/doc/mios/adr/0003-sbom-not-hardcode.md) | accepted | 2026-07-12 | 7, 8, 12 | `image.sidecars`, `build.bake_groups`, `build.bake_group` |
| 0004 | [GitHub ≡ Forgejo equal-publisher release topology](usr/share/doc/mios/adr/0004-github-forgejo-equal-publisher.md) | accepted | 2026-07-12 | 3, 4, 12 | `build.rechunk_max_layers`, `build.bake_groups`, `build.curl_trigger_fallback` |
| 0005 | ["Sovereign run-off-M: Hyper-V VHDX deployment"](usr/share/doc/mios/adr/0005-sovereign-run-off-m-drive.md) | accepted | 2026-07-12 | 2, 12 | `storage.cephfs`, `storage.cephfs.enable` |
| 0006 | [OpenAI-API-only AI contract (the governing AI standard)](usr/share/doc/mios/adr/0006-openai-api-only-ai-contract.md) | accepted | 2026-07-12 | 5 | `ai.endpoint`, `hermes.endpoint`, `ports.hermes`, `ports.agent_pipe`, +1 |
| 0007 | [Governance model — laws as fitness functions, ADRs as decisions, a generated MiOS Spec (OpenAI Model-Spec pattern)](usr/share/doc/mios/adr/0007-governance-model-laws-adrs-spec.md) | accepted | 2026-07-12 | 7, 8 | `laws`, `conventions` |
| 0008 | [MiOS-Cat unified entry point + repo minification](usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md) | proposed | 2026-07-16 | 1, 7, 8, 9, 12 | `cat`, `cat.repo_partition`, `cat.data_partition`, `cat.models`, +4 |
| 0009 | [Unified config surface — mios.toml ⇄ Portal + configurator + OpenAI /v1, all on the agent_pipe port](usr/share/doc/mios/adr/0009-unified-config-surface.md) | accepted | 2026-07-16 | 5, 7, 8 | `portal`, `ports.agent_pipe` |
| 0010 | [SSOT-as-system-dotfiles — one mios.toml projects every dotfile on every platform](usr/share/doc/mios/adr/0010-ssot-as-system-dotfiles.md) | accepted | 2026-07-16 | 1, 7, 8, 9, 13 | `dotfiles.registry`, `colors`, `theme`, `appearance`, +3 |
| 0011 | [Unified languages & compiled file-patterns — language-per-domain + one-template-per-type](usr/share/doc/mios/adr/0011-unified-languages-and-file-patterns.md) | proposed | 2026-07-16 | 7, 8, 9 | -- |
| 0012 | ["Float-latest: no hand-pinned versions across any artifact class"](usr/share/doc/mios/adr/0012-float-latest-no-hand-pinned-versions.md) | accepted | 2026-07-28 | 7, 8, 12 | `image.sidecars`, `build.bake`, `build.bake_groups`, `ai.bake_models` |
| 0013 | ["Deploy-surface consolidation behind installation/mios-install"](usr/share/doc/mios/adr/0013-deploy-surface-consolidation.md) | accepted | 2026-07-28 | 1, 7, 8, 9 | `install.target`, `cat.mode` |
| 0014 | ["The bootc-install bare-metal leg: bootc install to-disk --transport oci"](usr/share/doc/mios/adr/0014-bootc-install-bare-metal-leg.md) | proposed | 2026-07-28 | 3, 4, 12 | `image.sidecars`, `build.bake` |
| 0015 | ["Unified key library architecture & full de-duplication campaign"](usr/share/doc/mios/adr/0015-unified-key-library-architecture.md) | accepted | 2026-07-31 | 7, 8, 9, 13 | `build.bake`, `colors`, `ai`, `ports` |
| 0016 | ["Blade-Node topology — orthogonal lineage/role axes, and service offload as a URL overlay"](usr/share/doc/mios/adr/0016-blade-node-topology.md) | proposed | 2026-08-22 | 1, 3, 5, 7, 8, 9, 12 | `urls`, `ports`, `blades`, `nodes`, +4 |

<!-- derived from the front-matter of 16 file(s) under usr/share/doc/mios/adr/ -->

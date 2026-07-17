<!-- AI-hint: Index + process spec for MiOS Architecture Decision Records; read this first to learn the ADR format, status lifecycle, and which ADR governs the workstream you are implementing. -->
<!-- AI-related: usr/share/doc/mios/adr/*.md, usr/share/mios/mios.toml [laws], CLAUDE.md, AGENTS.md -->

# MiOS Architecture Decision Records (ADRs)

This directory is the immutable decision record of MiOS. It is baked into the
image (it lives under `/usr/share/doc/mios/adr/` on every deployed host), so a
running MiOS carries the *why* behind its own architecture — no external wiki,
no lost context. Each ADR is written to be **self-contained**: a future agent
(human or AI) can open one file and begin implementation without re-deriving the
surrounding context or reading five other documents. That is the whole point —
minimize the token/time cost of picking up a workstream cold.

## What an ADR is

An ADR captures **one architectural decision**: the problem, the forces, the
decision taken, why, the alternatives rejected, and the consequences. MiOS ADRs
follow the [MADR](https://adr.github.io/madr/) convention (Markdown Any Decision
Records) with a MiOS-specific AI-hint header and YAML frontmatter.

Three rules make the record trustworthy:

1. **Immutable.** Once an ADR is `accepted` it is not rewritten. Facts, paths,
   and status may be corrected, but the *decision* is frozen. If reality diverges
   from a decision, you do not edit the old ADR — you write a **new** ADR that
   supersedes it (see the lifecycle below).
2. **Numbered + append-only.** ADRs get a zero-padded sequence number
   (`0001`, `0002`, …) assigned once and never reused. New decisions append; the
   history is the sequence.
3. **One decision each.** If a change bundles two independent decisions, it is
   two ADRs. This keeps each record atomic, greppable, and individually
   supersedable.

## File format (every ADR follows this exactly)

An ADR is `NNNN-<slug>.md`. It opens with a two-line MiOS AI-hint header (a MiOS
convention that lets an agent grep the *purpose* and the *governed files* without
parsing the body), then YAML frontmatter, then the body sections.

```
<!-- AI-hint: <one line: what this decision is + why an agent reads it> -->
<!-- AI-related: <comma-list of the real files / SSOT keys this decision governs> -->
---
adr: NNNN
title: <title>
status: proposed | accepted | superseded
date: 2026-07-12
deciders: [operator, ai-pair]
tags: [<domain tags>]
laws: [<which of the 13 MiOS architectural laws this touches, by number>]
ssot_keys: [<mios.toml keys, e.g. build.bake, blade, image.sidecars>]
related_ws: [<WS-* workstream codes this ADR seeds or governs>]
supersedes: []          # ADR numbers this one replaces
superseded_by: []       # ADR numbers that later replaced this one
---

# ADR-NNNN: <title>

## Status
## Context
## Decision
## Rationale
## Alternatives considered
## Consequences
## Implementation
## References
```

### Frontmatter schema

| Key | Meaning |
|---|---|
| `adr` | The zero-padded sequence number, matching the filename. |
| `title` | Short imperative decision title. |
| `status` | One of `proposed`, `accepted`, `superseded` (see lifecycle). |
| `date` | ISO date the decision reached its current status. |
| `deciders` | Who decided. MiOS decisions are made by the `operator` in an `ai-pair` loop. |
| `tags` | Free-form domain tags for grouping/search. |
| `laws` | The MiOS architectural laws (1–13) this decision touches, by number. The law registry is `usr/share/mios/mios.toml [laws]` — the single numbering SSOT. |
| `ssot_keys` | The `mios.toml` keys (or `MIOS_*` env keys) this decision governs. |
| `related_ws` | The `WS-*` workstream codes this ADR seeds or governs. |
| `supersedes` / `superseded_by` | ADR-number cross-links for the lifecycle. |

## Status lifecycle

```
proposed ──accept──▶ accepted ──(a newer ADR replaces it)──▶ superseded
```

- **proposed** — drafted, under review; not yet load-bearing.
- **accepted** — the decision is in force. Implementation may be `DONE` or
  `PLANNED`; the ADR states which (accepted ≠ fully implemented).
- **superseded** — a later ADR replaced this decision. The superseded ADR is
  **kept, not deleted**: set its `status: superseded`, fill `superseded_by: [NNNN]`,
  and add a one-line note at the top of its Status section pointing forward. The
  replacing ADR lists the old number in `supersedes: [...]`. **Superseding is
  always a new ADR — never an in-place rewrite.** The old text remains readable so
  the reasoning trail survives.

## The MiOS architectural laws (context for the `laws` field)

Every ADR names the laws it touches. The 13 laws (v0.3.0) are the canonical
registry in `usr/share/mios/mios.toml [laws]` (`id/slug/applies_to/enforced_by`);
they are enforced by `automation/38-drift-checks.sh` (offline), `automation/99-postcheck.sh`
(at bake), and `bootc container lint`. For quick reference: 1 USR-OVER-ETC,
2 NO-MKDIR-IN-VAR, 3 BOUND-IMAGES, 4 BOOTC-CONTAINER-LINT, 5 UNIFIED-AI-REDIRECTS,
6 UNPRIVILEGED-QUADLETS, 7 NO-HARDCODE, 8 SSOT-PROJECTION, 9 ONE-CANONICAL-NAME,
10 BARE-SAFE-ENV, 11 SECRETS-NEVER-IN-ENV, 12 BAKE-NOT-FETCH, 13 NATIVE-DROPINS.

## The record

| ADR | Title | Status | Laws | Seeds / governs |
|---|---|---|---|---|
| [0001](0001-two-gate-bake-activation.md) | Two-gate bake / activation model | accepted | 3, 6, 7, 8, 12 | WS-BAKEGATE, WS-BLADE |
| [0002](0002-mios-sys-shared-base-consolidation.md) | MiOS-Sys shared-base sidecar consolidation | accepted | 3, 6, 7, 8, 12 | WS-MIOSSYS |
| [0003](0003-sbom-not-hardcode.md) | SBOM-not-hardcode: digests are build-resolved provenance | accepted | 7, 8, 12 | WS-SBOM |
| [0004](0004-github-forgejo-equal-publisher.md) | GitHub ≡ Forgejo equal-publisher release topology | accepted | 3, 4, 12 | WS-RELTOP |
| [0005](0005-sovereign-run-off-m-drive.md) | Sovereign run-off-M: Hyper-V VHDX deployment | accepted | 2, 12 | WS-MDRIVE |
| [0006](0006-openai-api-only-ai-contract.md) | OpenAI-API-only AI contract (the governing AI standard) | accepted | 5 | WS-DEPRED |
| [0007](0007-governance-model-laws-adrs-spec.md) | Governance model: laws as fitness functions, ADRs as decisions, generated MiOS Spec | accepted | 7, 8 | WS-DOCS |
| [0008](0008-mios-cat-unified-entry-and-minification.md) | MiOS-Cat unified entry point + repo minification | proposed | 1, 7, 8, 9, 12 | WS-CAT, WS-CATREPO, WS-CATFLAT |
| [0009](0009-unified-config-surface.md) | Unified config surface: mios.toml ⇄ Portal + configurator + /v1 at :8640/ | accepted | 5, 7, 8 | WS-CONFIG, WS-DEPRED |
| [0010](0010-ssot-as-system-dotfiles.md) | SSOT-as-system-dotfiles: one mios.toml projects every dotfile on every platform | accepted | 1, 7, 8, 9, 13 | WS-DOTFILES, WS-CONFIG |
| [0011](0011-unified-languages-and-file-patterns.md) | Unified languages & compiled file-patterns: language-per-domain + one-template-per-type | proposed | 7, 8, 9 | WS-LANG, WS-TEMPLATE, WS-DEBT |

## New MiOS decisions — how to add an ADR

1. Take the next free number. Create `NNNN-<slug>.md` from the format above.
2. Fill every frontmatter key. `laws` must reference real law numbers from the
   `[laws]` registry; `ssot_keys` must be real `mios.toml` keys.
3. Add a row to **The record** table above (this is the only edit an existing
   file receives when a new ADR lands, plus any `superseded_by` back-links).
4. If the decision replaces an earlier one, set `supersedes`/`superseded_by` on
   both, flip the old ADR to `status: superseded`, and leave its body intact.

## Background any ADR reader can assume

MiOS is an immutable, `bootc`/OCI-shaped Fedora system (`ghcr.io/mios-dev/mios:latest`,
`FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia`) that is **also** a local,
self-hosted, OpenAI-compatible agentic AI OS. You boot it, `bootc upgrade` it
like a `git pull`, and `bootc rollback` it like a Ctrl-Z. The one universal image
is designed to deploy anywhere, fully-featured, for sovereignty — your data and
your models stay on your hardware. The repo root **is** the deployed system root
(`usr/` here lands at `/usr` on the host). The single source of truth for every
operator-tunable value is `usr/share/mios/mios.toml`, resolved through a
vendor(`/usr`) < host(`/etc`) < user(`~/.config`) cascade. The build is one
`Containerfile` running `automation/NN-*.sh` in numeric order. Thirteen
architectural laws govern the tree; a failing law fails the build.

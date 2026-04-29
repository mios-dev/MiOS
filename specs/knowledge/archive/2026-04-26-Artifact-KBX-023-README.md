<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# MiOS Knowledge Base

This directory is the **AI-context reference library** for MiOS.
It collects every research compendium, technical reference, and
operational guide produced during the project's development, plus the
engineering-blueprint DOCX files and legacy changelogs.

Files here are **reference material**, not instructions. System Code,
Agent CLI, and other agents are expected to read from this directory
when they need background — but authoritative project rules live in:

- [`../../INDEX.md`](../../INDEX.md) — primary AI instruction file
- [`../../INDEX.md`](../../INDEX.md) — Agent mirror
- [`../../INDEX.md`](../../INDEX.md) — generic-agent mirror
- [`../../.github/Assistant-instructions.md`](../../.github/Assistant-instructions.md) — Assistant rules
- [`../../.ai-context/knowledge-base.md`](../../.ai-context/knowledge-base.md) — historical audit log
- [`../PACKAGES.md`](../PACKAGES.md) — single source of truth for packages

---

## Directory layout

```
specs/knowledge/
├── research/              ← technical-intelligence reports
├── guides/                ← operational / troubleshooting guides
└── blueprints/            ← engineering blueprint .docx files
```

---

## `AI-RESEARCH-TEMPLATE.md` — Standardized AI Reference
A universal template for AI harnesses and agents to ensure consistent context retrieval, memory mapping, and architectural documentation.

---

## `research/` — technical-intelligence reports

Long-form research produced while designing and debugging MiOS.
Read these when you need the *why* behind an architectural decision, or
when a new upstream ecosystem change (bootc, Universal Blue, NVIDIA CDI,
cosign, composefs, etc.) needs contextualizing.

| # | Document | Topic |
|---|----------|-------|
| 01 | `01-bootc-ecosystem-advances-2025-2026.md` | Bootc ecosystem strategic analysis for 2025-2026 |
| 02 | `02-building-mios-intelligence-report.md` | Complete technical intelligence report on MiOS architecture |
| 03 | `03-comprehensive-research-compendium.md` | Comprehensive research compendium — Fedora Rawhide bootc immutable workstation OS |
| 04 | `04-technical-reference-7-solutions.md` | 7 practical solutions for immutable workstation deployment |
| 05 | `05-upstream-adoption-playbook.md` | Upstream adoption playbook — sequencing plan for a signed, multi-variant Fedora bootc |
| 06 | `06-v2_1_6-release-implementation-plan.md` | v0.1.1 release: CI fix, cosign keyless signing, full implementation plan |
| 07 | `07-v2_1-resolving-build-failures.md` | v2.1: resolving every build and boot failure |
| 08 | `08-gnome-50-fedora-rawhide-package-guide.md` | GNOME 50 on Fedora Rawhide — complete package reference and configuration guide |
| 09 | `09-integrating-ceph-cephadm-k3s.md` | Integrating Ceph, Cephadm, and K3s into MiOS |
| 10 | `10-vfio-gpu-passthrough-fedora-2025.md` | Linux VFIO GPU passthrough tools on Fedora — 2025 packaging and ecosystem analysis |
| 11 | `11-minimal-gnome-strategy-analysis.md` | Minimal GNOME desktop strategy — package removal and build-up analysis |
| 12 | `12-minimal-gnome-definitive-strategy.md` | Minimal GNOME for Fedora Rawhide bootc — the definitive package strategy |
| 13 | `13-technical-audit-bootc-ecosystem.md` | Technical audit of the bootc ecosystem for MiOS |
| 14 | `14-upstream-bootc-ecosystem-fixes.md` | Upstream bootc ecosystem fixes — mapping runtime issues to proven solutions |
| 15 | `15-compass-artifact-1.md` | Compass research artifact 1 |
| 16 | `16-compass-artifact-2.md` | Compass research artifact 2 |

---

## `guides/` — operational / troubleshooting guides

Actionable guides for deploying and managing MiOS across various environments.

| Document | Topic |
|----------|-------|
| `WINDOWS-BUILD-WORKFLOW.md` | Building and deploying MiOS from Windows 11 using Podman Desktop |
| `WSL2-DEPLOYMENT.md` | Deploying MiOS in WSL2 and critical security mitigations |
| `cpu-isolation-guide.md` | Comprehensive guide to CPU core isolation for virtualization |
| `vfio-toolkit-readme.md` | Documentation for the MiOS VFIO and GPU passthrough toolkit |

**Reading order for a new collaborator / AI agent onboarding:**
→ 03 (compendium) → 02 (intelligence report) → 13 (audit) → 14 (fixes) → 01 (strategic direction) → topic-specific docs as needed.

---

## `guides/` — operational / troubleshooting guides

How-to material for the toolkit side of MiOS: VFIO passthrough,
CPU pinning for gaming / high-throughput VMs, Looking Glass display
capture, and the standalone full-system provisioning script.

| Document | Purpose |
|----------|---------|
| `cpu-isolation-guide.md` | CPU isolation — concept, kernel params, cgroup boundaries |
| `cpu-isolation-optimization-notes.md` | Optimization notes accumulated across builds |
| `WINDOWS-BUILD-WORKFLOW.md` | Windows 11 + Podman Desktop + WSL2/g build guide |
| `cpu-isolation-preset-corrections.md` | Preset corrections by CPU family (Zen 3/4/5, Intel hybrid) |
| `cpu-isolator-script-improvements.md` | Script-level improvements, idempotency, edge cases |
| `looking-glass-integration.md` | Looking Glass build + kvmfr + udev + Gamescope integration |
| `vfio-toolkit-readme.md` | VFIO configurator toolkit — passing GPUs / USB controllers into VMs |
| `vm-cpu-pin-manager-readme.md` | VM CPU pin manager — pinning vCPUs to host physical cores |
| `mios-full-script-readme.md` | Legacy `mios-full.sh` — standalone one-shot provisioner |

These documents describe the **out-of-image toolkit** that runs *on the
booted system*, not the build-time provisioning scripts. Build-time
logic lives in `../../automation/` and `../../`.

---

## `blueprints/` — engineering blueprint DOCX files

Formal engineering documents authored in Microsoft Word format. Read
these when you need the "executive summary" view of MiOS's
architecture.

| Document | Purpose |
|----------|---------|
| `MiOS-Engineering-Blueprint.docx` | Overall engineering blueprint |
| `MiOS-Blueprint.docx` | bootc-specific blueprint |

---

## `changelogs/` — Consolidated Version History (at project root)

Historical and detailed changelogs are now consolidated in the root [`/changelogs/`](../../changelogs/) directory.

| Document | Covers |
|----------|--------|
| [`01-v1.1-Legacy-Profiler.md`](../../changelogs/01-v1.1-Legacy-Profiler.md) | v1.1 legacy profiler documentation |
| [`02-v0.1.1-Detailed-Technical-Log.md`](../../changelogs/02-v0.1.1-Detailed-Technical-Log.md) | Detailed v2.1.x milestone technical logs |
| [`03-Cumulative-Changelog.md`](../../changelogs/03-Cumulative-Changelog.md) | Main cumulative project changelog |

**Do not** treat legacy changelogs as current state. Cross-reference
with [`03-Cumulative-Changelog.md`](../../changelogs/03-Cumulative-Changelog.md) and the `VERSION` file before acting on
anything here.

---

## How AI agents should use this directory

1. **Default to not reading.** The primary instruction files
   (`INDEX.md`, `INDEX.md`, `INDEX.md`) contain the rules. These
   research docs are background.
2. **When a question requires background**, search semantically:
   "How does NVIDIA CDI interact with bootc?" → read
   `10-vfio-gpu-passthrough-fedora-2025.md` and
   `09-integrating-ceph-cephadm-k3s.md`.
3. **When an upstream change lands that affects this project**,
   check if it's already tracked in `01-bootc-ecosystem-advances-2025-2026.md`
   or `14-upstream-bootc-ecosystem-fixes.md` before proposing a response.
4. **Never quote these documents as a source of hard rules.** The hard
   rules live in `INDEX.md` §3 and are the only rules. Research docs
   explain *why* the rules exist; they do not override them.
5. **DOCX blueprints require conversion before inline use.** If an
   agent needs their content programmatically, use `pandoc` or
   `python-docx` — don't attempt to read binary DOCX as text.

---

*This index is generated as part of the MiOS AI tooling
export. When documents are added or removed, regenerate the tables in
this file so it stays accurate.*

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

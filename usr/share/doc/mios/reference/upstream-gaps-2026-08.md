<!-- AI-HINT: Verified upstream-vs-MiOS report (2026-08) for the AI-lane container images and their CVE exposure. Continues upstream-gaps-2026-07.md. Every claim below was checked against a primary source (NVD, upstream release tags, registry APIs) and badged; the report also adjudicates a batch of externally-generated deep-research reports whose version numbers, registries, and fix-lines were partly fabricated. Use the reconciliation table to know what is real; do not cite the external reports directly.
     AI-related: usr/share/mios/mios.toml, mios-pgvector, mios-llm-heavy, mios-llm-heavy-alt, mios-llm-light, usr/libexec/mios/mios-resolve-latest, usr/share/doc/mios/reference/upstream-gaps-2026-07.md, usr/share/mios/prompts/upstream-research.xml.md -->

# Upstream-vs-MiOS Verification Report — 2026-08

This report continues the 2026-07 gap report with a different mandate: instead of
surveying upstream *features* MiOS lags, it **verifies upstream versions and CVEs
for the AI-lane container images against primary sources**, and reconciles a
two-week batch of externally-generated LLM deep-research reports (15 documents)
whose conclusions ranged from correct to fabricated. The repo SSOT
(`usr/share/mios/mios.toml`) wins every conflict.

Badge legend, applied per claim:

- **[VERIFIED]** — confirmed against a primary source (NVD/CVE record, upstream
  release tags, a registry's own tag API).
- **[PARTIALLY VERIFIED]** — the core claim is true but a detail (registry,
  fix version, severity) was wrong in the source material.
- **[CONTRADICTED]** — a primary source disproves it.

## Verified upstream state (AI-lane images)

| Component | MiOS ref (SSOT `[image.sidecars]`) | Verified upstream current | Badge | Primary source |
|---|---|---|---|---|
| pgvector | `docker.io/pgvector/pgvector:0.8.6-pg17` (bumped from `0.8.3-pg17` this pass) | 0.8.6 (git tag; project publishes tags, not GitHub Releases). `0.8.6-pg17` and `0.8.6-pg18` image tags both exist. | [VERIFIED] | github.com/pgvector/pgvector tags; hub.docker.com pgvector/pgvector tag API |
| PostgreSQL (inside pgvector image) | PG **17** major (pinned via the `-pg17` tag suffix) | PG 18 is the newest major (18.6 current minor); 17.x remains fully supported. | [VERIFIED] | postgresql.org/support/versioning |
| vLLM (`mios-llm-heavy`, gated) | `docker.io/vllm/vllm-openai:latest` (float-latest policy) | 0.27.1; the `v0.27.1` image tag exists. | [VERIFIED] | pypi.org/pypi/vllm/json; hub.docker.com vllm/vllm-openai tag API |
| SGLang (`mios-llm-heavy-alt`, gated) | `docker.io/lmsysorg/sglang:latest` (float-latest policy) | v0.5.17; `lmsysorg/sglang` is the official registry — **`ghcr.io/sgl-project/sglang` does not exist publicly** (external reports cited it throughout). | [VERIFIED] / registry claim [CONTRADICTED] | github.com/sgl-project/sglang releases; hub.docker.com + ghcr.io token probes |
| llama-swap (`mios-llm-light`) | `ghcr.io/mostlygeek/llama-swap:cuda` (moving tag) | v250; the plain `cuda` moving tag exists, versioned tags are `vNNN-cuda-bXXXXX` (llama-swap version + llama.cpp build). | [VERIFIED] | github.com/mostlygeek/llama-swap releases; ghcr.io tag list API |

## CVE matrix (deduplicated, MiOS-exposure adjudicated)

| CVE | Component | Verified severity | Affected / fixed | MiOS exposure | Disposition |
|---|---|---|---|---|---|
| CVE-2026-3172 | pgvector | CVSS 3.1 **8.1 High** (buffer overflow in parallel HNSW index build; integer underflow + OOB write, CWE-191/787) | 0.6.0–0.8.1 / fixed **0.8.2** | **None even before this pass** — MiOS pinned `0.8.3-pg17`, already past the fix line. The bump to `0.8.6-pg17` is latest-stable hygiene, not remediation. | Closed (pin bumped through the SSOT; all projections regenerated) |
| CVE-2026-71486 / GHSA-8737-qx52-hjff | vLLM | CVSS 3.1 **4.3 Medium** — external reports called it "High" [PARTIALLY VERIFIED]. Derender endpoints decode caller-supplied token IDs before output bounds → authenticated resource exhaustion (CWE-400/770). | < 0.26.0 / fixed **0.26.0** | Low: the heavy lane floats on `:latest` (0.27.1 > 0.26.0), is **gated off by default** (`[ai.vllm].enable = false` + `ConditionPathExists=/var/lib/mios/vllm/model/config.json`), and requires auth. | No action; float already carries the fix |
| CVE-2026-3059 / -3060 / -3989 | SGLang | 3059/3060: CVSS **9.8** unauthenticated RCE (pickle deserialization, CWE-502 — ZMQ broker + disaggregation module); 3989: CVSS 7.8 (`replay_request_dump.py`) | ≤ 0.5.9 / all fixed **0.5.10** — external reports claimed "fixed in 0.5.17" [CONTRADICTED on the fix line; CVEs themselves VERIFIED] | Low: `:latest` (0.5.17) is far past 0.5.10, lane gated off by default, loopback-adjacent. | No action; float already carries the fix |

Two CVE claims from the external reports were **dropped**: a LLaMA-Factory CVE
(MiOS does not ship LLaMA-Factory) and an unverifiable kernel CVE (the kernel is
inherited from the Fedora CoreOS base of `ucore-hci:stable-nvidia`, so the
actionable surface is base-image tracking, not a MiOS patch).

## Findings

### 1. pgvector pin lagged latest stable (closed this pass)
- **Upstream:** pgvector 0.8.6 with `0.8.6-pg17` image tag published.
- **MiOS state (before):** `mios.toml [image.sidecars].pgvector = "docker.io/pgvector/pgvector:0.8.3-pg17"` — the only exact-pinned AI image, per its own comment "Bump via Renovate or operator".
- **Resolution:** bumped to `0.8.6-pg17` in the three SSOT sites (`[image.sidecars]`, `[build.bake].core`, `[containers.mios-pgvector.Container].Image` fallback) plus `usr/lib/mios/bake/plan.d/04-extra.list`, then regenerated every projection via `tools/sync-generated.sh`. The PG major stays **17**: `/var/lib/mios/pgvector` holds a PG17 data dir, and a `-pg18` image refuses a PG17 cluster without `pg_upgrade` (tracked as its own task; see WS-UPSTREAM). A 0.8.x→0.8.6 extension update needs no forced reindex; `ALTER EXTENSION vector UPDATE` applies on the next major-touch window (extension name is `vector`, version column `pg_extension.extversion`).

### 2. `mios-resolve-latest` ref list drifted from the SSOT (closed this pass)
- **MiOS state (before):** `usr/libexec/mios/mios-resolve-latest` hardcoded `pgvector:pg16`, `open-webui:latest`, `valkey:8.0`, `ceph:v18` — four refs disagreeing with `[image.sidecars]`/`[versions]` (`0.8.x-pg17`, `:main`, `:latest`, `v19`), so its SBOM rows recorded images MiOS does not ship.
- **Resolution:** literals corrected to the SSOT values. The structural fix — deriving the list from `mios.toml` instead of mirroring it — is tracked in WS-UPSTREAM.

### 3. Renovate does not manage the pins its SSOT comment promises
- **MiOS state:** `mios.toml` says the pgvector pin is bumped "via Renovate or operator", but `renovate.json`'s only custom manager covers the Containerfile `ARG BASE_IMAGE` line. No manager watches `[image.sidecars]`, `usr/lib/mios/bake/plan.d/*.list`, or Quadlet `Image=` lines — so every exact pin (pgvector, k3s) rots until an operator notices.
- **Recommendation:** add a `customManagers` regex for `usr/share/mios/mios.toml` `[image.sidecars]` exact-pinned entries (datasource docker), leaving `:latest`/`:main` floats alone. Tracked in WS-UPSTREAM.

### 4. Three mutually inconsistent port/lane schemes in the docs
- **MiOS state:** the runtime SSOT (`mios.toml [ports]`, projected into `automation/lib/globals.sh`) says `llm_light=8500, vllm=8520 (mios-llm-heavy), sglang=8530 (mios-llm-heavy-alt), pgvector=8600, agent_pipe=8700, prefilter=8710, hermes=8720, searxng=8800, opencode_gateway=8780`. README.md/`api.md`/GEMINI.md/SECURITY.md still document the retired `:11450/:11441/:11440/:5432/:8888` scheme, and CLAUDE.md documents a third (`:8450/:8441/:8442/:8432/:8899`). Several docs also swap which heavy lane is vLLM vs SGLang (the Quadlets are unambiguous: `mios-llm-heavy` runs vLLM, `mios-llm-heavy-alt` runs SGLang and is marked deprecated).
- **Why it matters beyond tidiness:** the external research reports inherited the stale README numbers and "corrected" real values back to wrong ones — doc drift here actively corrupts downstream automated research.
- **Recommendation:** re-render the doc port/lane tables from `[ports]` (the same projection discipline `check_ports_category_schema` already enforces for the flat table). Tracked in WS-UPSTREAM.

### 5. Kernel lockdown was asserted at build, never verified at runtime (closed this pass)
- **MiOS state (before):** `lockdown=integrity` ships in `usr/lib/bootc/kargs.d/` and is projection-checked (`check_kargs_projection`, `check_uki_cmdline_projection`), but no boot-time health check confirmed the running kernel honors it.
- **Resolution:** added `usr/lib/greenboot/check/wanted.d/31-kernel-lockdown.sh` — warn-tier greenboot probe asserting `/sys/kernel/security/lockdown` reports `[integrity]`, degrading open on kernels without the lockdown LSM (WSL2). Complements the existing `30-nvidia-cdi.sh` GPU/CDI probe and the `nvidia-ctk >= 1.18` bake gate in `automation/99-postcheck.sh`; together these cover what the external reports proposed as a "kernel rebase test" (the kernel itself is FCOS-inherited and not a MiOS-controlled action).

### 6. External LLM deep-research reports require adversarial verification
- **Observed failure modes across the 15-report batch:** fabricated point releases for bootc/systemd/Podman and a nonexistent kernel stable line; a nonexistent registry (`ghcr.io/sgl-project/sglang`) cited as canonical; a wrong CVE fix line (SGLang pickle CVEs attributed to 0.5.17, actually 0.5.10); severity inflation (CVE-2026-71486 reported High, actually 4.3 Medium); invented CLI flags, SQL catalogs, and Quadlet keys; and stale MiOS facts inherited from drifted docs (finding 4).
- **What survived verification:** the CVE identifiers themselves, the pgvector/vLLM/SGLang version arcs (off by one to several releases), and the correct registries for vLLM/pgvector.
- **Resolution:** a corrected, SSOT-grounded research prompt now ships at `usr/share/mios/prompts/upstream-research.xml.md` (primary-sources-only, badge-per-claim, never-invent rules), so scheduled research (`usr/libexec/mios/mios-scheduled-research`) and operator-driven passes start from framing that matches this repo instead of its stale mirrors.

## Cross-refs

- `usr/share/doc/mios/reference/upstream-gaps-2026-07.md` — the feature-gap predecessor to this report.
- `usr/share/doc/mios/upstream/inference-engines.md` §Lanes — the per-engine upstream doc (vLLM / SGLang / llama.cpp+llama-swap).
- `usr/share/doc/mios/upstream/pgvector.md` §Versioning — pin policy and the PG-major migration path.
- `usr/share/mios/prompts/upstream-research.xml.md` — the corrected research-prompt contract.
- `ROADMAP.md` §WS-UPSTREAM — the workstream tracking the open items above.
- `SECURITY.md` — disclosure process; this report is a verification record, not an advisory.

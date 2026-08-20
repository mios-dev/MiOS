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
| pgvector | `docker.io/pgvector/pgvector:pg18` (floated this pass, was the exact pin `0.8.3-pg17`) | 0.8.6 (git tag; project publishes tags, not GitHub Releases). The `pgNN` family tags float; `pg13`-`pg18` all publish. | [VERIFIED] | github.com/pgvector/pgvector tags; hub.docker.com pgvector/pgvector tag API |
| PostgreSQL (inside pgvector image) | PG **18** major (the `pg18` family tag) | PG 18 is the newest major (18.6 current minor). Moved this pass; existing PG17 clusters migrate via `mios-pgvector-major-upgrade.service`. | [VERIFIED] | postgresql.org/support/versioning |
| vLLM (`mios-llm-heavy`, gated) | `docker.io/vllm/vllm-openai:latest` (float-latest policy) | 0.27.1; the `v0.27.1` image tag exists. | [VERIFIED] | pypi.org/pypi/vllm/json; hub.docker.com vllm/vllm-openai tag API |
| SGLang (`mios-llm-heavy-alt`, gated) | `docker.io/lmsysorg/sglang:latest` (float-latest policy) | v0.5.17; `lmsysorg/sglang` is the official registry — **`ghcr.io/sgl-project/sglang` does not exist publicly** (external reports cited it throughout). | [VERIFIED] / registry claim [CONTRADICTED] | github.com/sgl-project/sglang releases; hub.docker.com + ghcr.io token probes |
| llama-swap (`mios-llm-light`) | `ghcr.io/mostlygeek/llama-swap:cuda` (moving tag) | v250; the plain `cuda` moving tag exists, versioned tags are `vNNN-cuda-bXXXXX` (llama-swap version + llama.cpp build). | [VERIFIED] | github.com/mostlygeek/llama-swap releases; ghcr.io tag list API |

## CVE matrix (deduplicated, MiOS-exposure adjudicated)

| CVE | Component | Verified severity | Affected / fixed | MiOS exposure | Disposition |
|---|---|---|---|---|---|
| CVE-2026-3172 | pgvector | CVSS 3.1 **8.1 High** (buffer overflow in parallel HNSW index build; integer underflow + OOB write, CWE-191/787) | 0.6.0–0.8.1 / fixed **0.8.2** | **None even before this pass** — MiOS was already at `0.8.3-pg17`, past the fix line. | Closed (the ref now floats on `pg18`, so every build re-resolves to newest) |
| CVE-2026-71486 / GHSA-8737-qx52-hjff | vLLM | CVSS 3.1 **4.3 Medium** — external reports called it "High" [PARTIALLY VERIFIED]. Derender endpoints decode caller-supplied token IDs before output bounds → authenticated resource exhaustion (CWE-400/770). | < 0.26.0 / fixed **0.26.0** | Low: the heavy lane floats on `:latest` (0.27.1 > 0.26.0), is **gated off by default** (`[ai.vllm].enable = false` + `ConditionPathExists=/var/lib/mios/vllm/model/config.json`), and requires auth. | No action; float already carries the fix |
| CVE-2026-3059 / -3060 / -3989 | SGLang | 3059/3060: CVSS **9.8** unauthenticated RCE (pickle deserialization, CWE-502 — ZMQ broker + disaggregation module); 3989: CVSS 7.8 (`replay_request_dump.py`) | ≤ 0.5.9 / all fixed **0.5.10** — external reports claimed "fixed in 0.5.17" [CONTRADICTED on the fix line; CVEs themselves VERIFIED] | Low: `:latest` (0.5.17) is far past 0.5.10, lane gated off by default, loopback-adjacent. | No action; float already carries the fix |

Two CVE claims from the external reports were **dropped**: a LLaMA-Factory CVE
(MiOS does not ship LLaMA-Factory) and an unverifiable kernel CVE (the kernel is
inherited from the Fedora CoreOS base of `ucore-hci:stable-nvidia`, so the
actionable surface is base-image tracking, not a MiOS patch).

## Findings

### 1. pgvector was the one hand-pinned AI image (closed this pass)
- **Upstream:** pgvector publishes floating `pgNN` family tags (`pg13`-`pg18`) alongside exact `<version>-pg<major>` tags.
- **MiOS state (before):** `mios.toml [image.sidecars].pgvector = "docker.io/pgvector/pgvector:0.8.3-pg17"` — the only hand-pinned AI image, per its own comment "Bump via Renovate or operator", and a release behind.
- **Resolution:** floated to `pg18` in the three SSOT sites (`[image.sidecars]`, `[build.bake].core`, `[containers.mios-pgvector.Container].Image` fallback) plus `usr/lib/mios/bake/plan.d/04-extra.list`, then regenerated every projection via `tools/sync-generated.sh`. The PostgreSQL major moved 17 -> 18 in the same pass, which is only safe because `mios-pgvector-major-upgrade.service` now migrates an existing cluster: it dumps the old cluster with an image of the OLD major into `[pgvector].restore_sql` (bind-mounted into `docker-entrypoint-initdb.d`), stashes rather than deletes the old data dir, and touches nothing at all if the dump cannot be taken. k3s is the one ref that cannot float — it publishes no usable channel tag, and `automation/06-enable-external-repos.sh` parses the Kubernetes repo minor out of its version-shaped tag (a `latest` tag would make that grep fall through to a stale hardcoded `1.36`), so it stays version-shaped and is bumped by Renovate instead of by hand; it was a patch behind and is now `v1.36.3-k3s1`. A 0.8.x→0.8.6 extension update needs no forced reindex; `ALTER EXTENSION vector UPDATE` applies on the next major-touch window (extension name is `vector`, version column `pg_extension.extversion`).

### 2. `mios-resolve-latest` ref list drifted from the SSOT (closed this pass)
- **MiOS state (before):** `usr/libexec/mios/mios-resolve-latest` hardcoded `pgvector:pg16`, `open-webui:latest`, `valkey:8.0`, `ceph:v18` — four refs disagreeing with `[image.sidecars]`/`[versions]` (`0.8.x-pg17`, `:main`, `:latest`, `v19`), so its SBOM rows recorded images MiOS does not ship.
- **Resolution:** literals corrected to the SSOT values. The structural fix — deriving the list from `mios.toml` instead of mirroring it — is tracked in WS-UPSTREAM.

### 3. Renovate did not manage the pins its SSOT comment promised (closed this pass)
- **MiOS state (before):** `mios.toml` said the pgvector pin is bumped "via Renovate or operator", but `renovate.json`'s only custom manager covered the Containerfile `ARG BASE_IMAGE` line. Nothing watched `[image.sidecars]`, so a hand-pinned ref rotted until an operator noticed — which is exactly what had happened.
- **Resolution:** most refs no longer need a bot at all (finding 1 floats them). The one that cannot float is k3s, and a `customManagers` regex now covers it: it matches version-shaped refs in `usr/share/mios/mios.toml` and leaves every float (`:latest`/`:main`/`pgNN`/major-only/`localhost/`) alone. `pinDigests` is **false** on it deliberately — the repo-level `docker:pinDigests` preset would otherwise write the `@sha256` literal that ADR-0003 and `check_no_hardcode_version` forbid, i.e. the bot would open PRs that fail the repo's own gate.

### 4. Three mutually inconsistent port/lane schemes in the docs
- **MiOS state:** the runtime SSOT (`mios.toml [ports]`, projected into `automation/lib/globals.sh`) says `llm_light=8500, vllm=8520 (mios-llm-heavy), sglang=8530 (mios-llm-heavy-alt), pgvector=8600, agent_pipe=8700, prefilter=8710, hermes=8720, searxng=8800, opencode_gateway=8780`. README.md/`api.md`/GEMINI.md/SECURITY.md still document the retired `:11450/:11441/:11440/:5432/:8888` scheme, and CLAUDE.md documents a third (`:8450/:8441/:8442/:8432/:8899`). Several docs also swap which heavy lane is vLLM vs SGLang (the Quadlets are unambiguous: `mios-llm-heavy` runs vLLM, `mios-llm-heavy-alt` runs SGLang and is marked deprecated).
- **Why it matters beyond tidiness:** the external research reports inherited the stale README numbers and "corrected" real values back to wrong ones — doc drift here actively corrupts downstream automated research.
- **Recommendation:** re-render the doc port/lane tables from `[ports]` (the same projection discipline `check_ports_category_schema` already enforces for the flat table). Tracked in WS-UPSTREAM.

### 4b. The generated k3s manifests carry pre-existing image drift
- **MiOS state:** `usr/share/mios/k3s/generated/*.yaml` are emitted by `tools/generate-k3s-manifests.sh`, which needs a live podman with the pods running — so they can only be refreshed on a MiOS host, not in CI or a plain checkout. `mios-webtools.yaml` still names `docker.io/library/redis:7-alpine` where the SSOT has moved the sidecar to `docker.io/valkey/valkey:latest`; that drift predates this pass and is **not** corrected here.
- **What was corrected:** the `mios-ai.yaml` pgvector ref, which this pass would otherwise have left stale (its other three refs already track the SSOT floats).
- **Recommendation:** regenerate all three on a podman-capable host, or teach the generator to render from `[containers.*]` so a checkout can refresh them like every other projection.

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

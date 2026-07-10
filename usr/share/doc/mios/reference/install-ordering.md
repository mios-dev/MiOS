<!-- AI-hint: The WS-DEPLOY workstream -- refactor + reorder the MiOS install/first-boot pipeline into a logical dependency DAG so a "missing dependency / not-ready / not-yet-built" state is structurally impossible: readiness-gated ordering + atomic, retried, idempotent, completeness-checked build steps. Grounded in concrete first-install failures. Sibling of WS-NAME in the streamlining/hardening campaign. -->
<!-- AI-related: automation/38-hermes-agent.sh, usr/libexec/mios/mios-ai-firstboot, usr/libexec/mios/mios-webtools-firstboot.sh, usr/libexec/mios/forge-firstboot.sh, automation/build.sh, Containerfile, build-mios.ps1 -->

# WS-DEPLOY — Install/first-boot pipeline reorder + dependency-completeness

**Status:** planned (workstream) · **Source:** operator directive 2026-07-10 · **Effort:** L (phased)
**Sibling of:** [WS-NAME](naming-unification.md) — same streamlining/hardening campaign.

## Goal

Refactor + reorder the install and first-boot steps into a **logical dependency
DAG** so that a **"missing dependency / prerequisite not ready / artifact not yet
built"** state is **structurally impossible** — not merely retried after the fact.
Every step (a) runs only after the things it needs are *ready* (not just started),
(b) installs/builds its outputs **atomically, idempotently, and with retry**, and
(c) self-verifies completeness before declaring success. A fresh install must
deploy a fully-working system every time.

## Why (concrete first-install failures, 2026-07-10)

Every failure on the operator's clean reinstall was an ordering / completeness bug,
not a logic bug:

| Symptom | Root cause (ordering/completeness) |
|---|---|
| `mios-agent-pipe` crash-loop: `No module named 'smolagents'` | `38-hermes-agent.sh` venv build ran once, failed on a transient network blip under install-time dnf/image-pull contention, `rm -rf`'d the venv, gave up. Deps installed piecemeal (smolagents a fragile *separate* step) instead of atomically from `requirements.txt`. **(fixed 31a52fb1 — the template for the pattern.)** |
| DB seeding skipped: `psycopg not installed`; `KeyError: 'uid'` in the seeder | Cascade of the missing venv — the seeder fell back to a system python without `psycopg`. |
| `mios-forge-firstboot` FAILED: *"Forgejo did not become ready within 300s"* | first-boot bootstrap gated on a *fixed timeout* instead of true readiness; the forge container was still starting under load. Recovered on a plain re-run. |
| `mios-webtools-crawl4ai` can't pull `localhost/mios-crawl4ai-slim:latest` | the local image (built by `mios-webtools-firstboot.sh` from `crawl4ai/Containerfile`) was never built — its build failed under contention, and the consumer started anyway. |
| install stalled ~20 min downloading a **deprecated** ollama CLI | dead step still in the fetcher sequence. **(removed df695faa.)** |

Common shape: **a consumer starts before its producer has finished**, and
**producers give up on first failure** instead of being atomic + retried + verified.

## The refactor

1. **Model the DAG explicitly.** Enumerate producers→consumers across
   `automation/NN-*.sh` (build-time) and the `*-firstboot` units (runtime):
   base packages → agent venv (`38-hermes-agent.sh`) → agent-pipe/hermes/gateway;
   pgvector-ready → DB seeding; forge-ready → forge-firstboot; local-image-built →
   webtools/crawl4ai/firecrawl; llama GGUFs → llm-light. Encode edges as systemd
   `After=`/`Requires=`/`BindsTo=` + `ConditionPathExists=` on the produced artifact.
2. **Readiness gates, not timeouts.** Replace "wait N seconds then abort" with a
   poll on the dependency's real readiness signal (health endpoint / socket / row /
   file), with a generous cap + `Restart=on-failure` so a slow producer under load
   never hard-fails a consumer.
3. **Atomic + retried + idempotent producers.** Every build/install step installs
   its COMPLETE output set in one transaction, retried with backoff, and is safe to
   re-run. The `38-hermes-agent.sh` fix (install `-r requirements.txt` + all deps in
   one retried transaction) is the reference pattern — apply it to the webtools
   image build, the sandbox image build, GGUF/vLLM fetches, and forge bootstrap.
4. **Per-phase completeness self-check.** Each phase verifies its artifacts exist
   (venv has *all* imports, image is in `podman images`, port is listening, seed row
   present) before writing its sentinel; `mios-ai-firstboot`'s
   `incomplete (...) -- retrying next boot` model, generalized to every producer,
   and triggered without requiring a full reboot.
5. **Order the fetcher/overlay sequence logically** and delete dead steps (ollama)
   so nothing downstream waits on a producer that will never succeed.

## Phasing

- **Phase 0 — inventory the DAG** (producers, consumers, edges, current gating).
- **Phase 1 — make every producer atomic+retried+idempotent+self-checking**
  (venv done; webtools image, sandbox image, GGUF/vLLM, forge next).
- **Phase 2 — convert consumers from timeouts to readiness gates** (systemd
  `After=`/`Condition*=` + poll-on-signal).
- **Phase 3 — reorder the overlay/automation sequence** to the DAG topological
  order; add a drift-gate that fails the build if a consumer unit lacks an `After=`
  on its producer (static DAG-integrity check).

## Drift-gate

New `automation/38-drift-checks.sh` check: parse the producer→consumer map and FAIL
if any consumer unit/step can start before its producer's readiness artifact exists
(missing `After=`/`ConditionPathExists=`), or if a producer lacks a retry/complete-
ness guard. Makes "missing dependency at install" a build-time error, not a
runtime surprise.

## Blast radius & risks

- Touches `automation/*-firstboot`/`38-*`, the `*-firstboot.sh` libexec scripts,
  and the systemd unit `After=`/`Requires=` graph — broad but mechanical.
- Risk: over-tight `Requires=` can cascade a stop; prefer `After=` +
  `ConditionPathExists=` + `Restart=on-failure` (degrade-open, never hard-cascade).
- Verify each phase on a clean `podman-MiOS-DEV` reinstall (the exact repro that
  surfaced these).

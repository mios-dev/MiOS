<!-- AI-hint: Stage-4 bake-in of the 2026-09-24 mios-ai-training-data-artifact (epistemic-evolution-and-learning-loop.md Stage 4) -- preserved audit bullets and training-corpus provenance, not independently verified.
     AI-related: mios-ai-training-data-artifact-2026-09-24.tar.gz, usr/share/doc/mios/knowledge/epistemic-evolution-and-learning-loop.md, usr/share/doc/mios/reference/upstream-registry.md, docs/research/spike-vscode-edge-to-edge-terminal.md -->
# Upstream Audit & Training-Corpus Bake-in (2026-09-24)

Source: `mios-ai-training-data-artifact-2026-09-24.tar.gz` (repo root), the
daily output of `automation/cicd/01-ingest-daily-telemetry.sh` →
`02-distill-agent-weights.py` per Stage 3/4 of the epistemic evolution loop.

## Preserved upstream bullets (unverified — synthetic telemetry, not a primary source)

The artifact's `contracts/UPSTREAM_AUDIT.md` and `sources/cve-audits/` record:

- Linux Kernel 7.2.8 — CXL host bridge decode fix
- Podman 5.8.2 / crun 1.20 — hardened pasta rootless namespace detach
- bootc 1.16.14 — composefs metadata signature validation
- Tetragon 1.4.3 — eBPF tracepoint hardening (telemetry: 1.85ms out-of-process latency, `pass: true`)
- SGLang 0.5.20 execution engine
- MCP SDK v2.0.2 — RFC-8832 compliance

These are one-line claims from a generated training artifact, not vendor
changelogs. Per the `/research` skill (primary sources first), do **not**
bump `image-versions.yml` / `usr/share/mios/mios.toml` pins from this list
alone — corroborate each against the vendor release notes before pinning.

## Training-corpus provenance

`dataset_info.json`: `mios-agent-tuning-corpus-2026-09-24`, HuggingFace TRL
conversational format, 4 SFT + 4 DPO samples, target model
`mios-micro / llama-3.3-70b-instruct`, specialist modules:
`bootc-security`, `crun-namespace`, `tetragon-ebpf`, `cli-shortcuts-and-sigils`.

The bundled `automation/*.sh|py` and `.devcontainer/` inside the tarball are
an earlier, stub-only snapshot of the real `automation/cicd/01-ingest-daily-telemetry.sh`
and `automation/cicd/02-distill-agent-weights.py` (both already more complete
in-tree) and are preserved as-is for training-data fidelity; they were not
back-ported over the real pipeline scripts.

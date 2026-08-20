<!-- AI-hint: Upstream reference for the three inference engines behind the MiOS lanes — llama.cpp via the llama-swap proxy (mios-llm-light, primary), vLLM (mios-llm-heavy, gated) and SGLang (mios-llm-heavy-alt, gated/deprecated) — covering what each engine is, the official images and registries, version/CVE tracking policy, and how each maps onto the MiOS Quadlets and mios.toml SSOT keys.
     AI-related: mios-llm-light, mios-llm-heavy, mios-llm-heavy-alt, mios-llm-worker@, mios-cpu-node, usr/share/mios/llamacpp/mios-llm-light.yaml, usr/share/mios/mios.toml, usr/libexec/mios/mios-resolve-latest -->

# Inference engines — llama.cpp/llama-swap, vLLM, SGLang

> Used by MiOS for: every local inference lane. `mios-llm-light` (llama.cpp
> behind the llama-swap proxy) is the always-on primary lane serving chat,
> embeddings and the coder model; `mios-llm-heavy` (vLLM) and
> `mios-llm-heavy-alt` (SGLang) are the gated dGPU lanes serving the
> `mios-heavy` model name. All three speak the OpenAI-compatible API behind
> `MIOS_AI_ENDPOINT` (Law 5).
> Source: `usr/share/mios/mios.toml` §[image.sidecars] + §[containers.mios-llm-*],
> `usr/share/containers/systemd/mios-llm-*.container`,
> `usr/share/doc/mios/reference/api.md` §Lanes.

## Why this matters to MiOS

MiOS is one thing built two ways at once: an immutable, bootc/OCI-shaped Fedora
workstation that is *also* a local, self-hosted, agentic AI operating system.
The engines documented here are the second half's muscle — they are consumed as
**container images, never pip installs**, so the same bootc discipline that
versions the OS versions the inference stack. Which engine serves a request is
an implementation detail behind one OpenAI-compatible surface; lanes are named
by *function* (`light`/`heavy`/`heavy-alt`), not by upstream tool.

## Projects

- llama.cpp — <https://github.com/ggml-org/llama.cpp> (MIT). GGUF-native
  CPU/CUDA inference server (`llama-server`).
- llama-swap — <https://github.com/mostlygeek/llama-swap> (MIT). Single-binary
  proxy that model-swaps multiple `llama-server` instances behind one endpoint.
  Releases are `vNNN`; image tags pair proxy and llama.cpp build as
  `vNNN-cuda-bXXXXX`, with `cuda` as the moving tag MiOS consumes.
- vLLM — <https://github.com/vllm-project/vllm> (Apache-2.0). PagedAttention
  serving engine; official image `docker.io/vllm/vllm-openai`.
- SGLang — <https://github.com/sgl-project/sglang> (Apache-2.0).
  RadixAttention serving engine; official image `docker.io/lmsysorg/sglang`.
  There is **no public `ghcr.io/sgl-project/sglang`** — external documents that
  cite one are wrong.

## Engine → lane mapping

| Lane (Quadlet) | Engine | Image (SSOT `[image.sidecars]` key) | Port (`[ports]` key) | Default state |
|---|---|---|---|---|
| `mios-llm-light.container` | llama.cpp via llama-swap | `ghcr.io/mostlygeek/llama-swap:cuda` (`cuda`, `llm_light`) | `llm_light` = 8500 | on, gated by `llamacpp/models/.ready` |
| `mios-llm-heavy.container` | vLLM | `docker.io/vllm/vllm-openai:latest` (`vllm`) | `vllm` = 8520 | **off** (`[ai.vllm].enable=false` + weights-gate) |
| `mios-llm-heavy-alt.container` | SGLang | `docker.io/lmsysorg/sglang:latest` (`sglang`) | `sglang` = 8530 | **off**, marked deprecated in the Quadlet header |
| `mios-cpu-node.container` / `mios-llm-worker@.container` | llama.cpp (`llama-server`) | `ghcr.io/mostlygeek/llama-swap:cuda` (`cuda`) | `cpu_node` = 8510 / per-instance | worker fan-out |

All lane Quadlets join `mios-ai.pod` (`Network=host`), so ports bind through
`Exec=` arguments, not `PublishPort=`. The light lane's model map is
`usr/share/mios/llamacpp/mios-llm-light.yaml` (hand-maintained; its comments
carry the llama.cpp build caveats that matter).

## Version & CVE policy

- **Float-latest, SBOM-pinned** (ADR-0012, WS-SBOM / WS-DEDUP-GUP56): the vLLM and SGLang
  refs deliberately float on `:latest`; the build resolves each floating ref to
  a digest and records it (`usr/share/mios/artifacts/sbom/bound-images.tsv`,
  `usr/libexec/mios/mios-resolve-latest`). Hand-pinning an exact engine version
  in the SSOT is a Law-7 violation caught by `check_no_hardcode_version` —
  CVE response for these lanes is "rebuild so `:latest` re-resolves", not a pin.
- Both heavy lanes ship **gated off** and their images are in
  `firstboot_tokens` (web-pulled at first boot, not bootc-bound) — exposure to
  an engine CVE requires the operator to have enabled the lane.
- Known-good floor as of the 2026-08 verification pass: vLLM ≥ 0.26.0
  (CVE-2026-71486, CVSS 4.3) and SGLang ≥ 0.5.10 (pickle-deserialization RCEs
  CVE-2026-3059/-3060, CVSS 9.8, and CVE-2026-3989) — `:latest` on both
  registries is far past both floors. Details:
  `usr/share/doc/mios/reference/upstream-gaps-2026-08.md` §CVE matrix.

## Cross-refs

- `usr/share/doc/mios/reference/upstream-gaps-2026-08.md` — verified versions/CVEs and the reconciliation record.
- `usr/share/doc/mios/reference/upstream-gaps-2026-07.md` §inference-lanes — feature gaps (FP8 KV, spec decode, CUDA graph).
- `usr/share/doc/mios/upstream/pgvector.md` — the memory-store peer of these lanes.
- `usr/share/doc/mios/upstream/nvidia.md` + `cdi.md` — how the lanes see the GPU.
- `ROADMAP.md` §WS-UPSTREAM — open upstream-tracking tasks.

NOTE TO ORCHESTRATOR: The target file is 478KB / 11,073 lines (a verbatim source-bundle of ~74 build scripts). It cannot be round-tripped through a single tool result (Bash truncates ~30KB; Read caps 256KB), and the SOT forbids inventing/transcribing script bodies. ALL refactor edits have therefore been applied IN PLACE on disk via the harness-tracked Edit tool (exact, complete, verified) at C:\MiOS\usr\share\doc\mios\reference\build-scripts.md. The file is final and ready as-is. The complete set of AUTHORED/CHANGED blocks (verbatim as they now appear in the file; all other content is unchanged verbatim build-script source preserved on disk) follows:

=== BLOCK 1: header + new "Purpose and place in MiOS" intro (replaces old AI-hint header + 5-line intro) ===
<!-- AI-hint: Reference snapshot bundling the source and execution order of the scripts that build the MiOS OCI image, so an agent can locate and read specific build logic without crawling the repo. Curated point-in-time copy; the live source-of-truth is the repo itself (automation/*.sh, tools/, Containerfile, Justfile).
     AI-related: install.sh, /tmp/build/automation/lib/packages.sh, ./tools/lib/userenv.sh, build.sh, automation/lib/packages.sh, profile.d/mios-motd.sh, /etc/mios/ai/system-prompt.md, /etc/mios/profile.toml, /usr/share/mios/profile.toml, /etc/mios/install.env
     AI-functions: toml_get, toml_get_array_csv, resolve_profile_layers, toml_get_layered, load_profile_defaults, log_info, log_ok, log_warn, log_err, log_phase, spin_start, spin_stop -->
# 'MiOS' Build Scripts -- Full Source Bundle

## Purpose and place in MiOS

MiOS is one system built two ways at once: an **immutable bootc/OCI Fedora
workstation** — the whole OS is a single container image you boot, `bootc upgrade`
like a `git pull`, and `bootc rollback` like a Ctrl-Z — that is *also* a **local,
self-replicating, agentic AI operating system**. The same image that ships
GNOME/Wayland, NVIDIA+ROCm+iGPU via CDI, KVM/libvirt with VFIO passthrough, and a
k3s+Ceph one-node-cluster path also ships a full local agent stack behind one
OpenAI-compatible endpoint.

**This document is the build half of that story.** The scripts collected here are
what turn the repo into the image: from the public bootstrap (`mios-bootstrap`),
through the `Containerfile` and the numbered `automation/NN-*.sh` pipeline, to the
finalize/cleanup/postcheck steps and the artifact cutters (RAW/ISO/qcow2/VHDX/WSL2).
That image is then consumed by the **bootc lifecycle** — `bootc switch`/`upgrade`
deploys it and `bootc rollback` reverts it — which is why keeping the pipeline
deterministic and correctly ordered is load-bearing for the whole system. The
build pipeline also *bakes in* the agentic plane: the inference lanes
(`mios-llm-light` on `:11450`, the gated heavy lanes `mios-llm-heavy`/`-alt`), the
`agent-pipe`/MiOS-Hermes orchestration, the PostgreSQL+pgvector memory, and the
MCP/A2A tool/agent surfaces all ship inside this same image as bound Quadlets.

The document doubles as a lookup: every script that participates in building the
MiOS OCI image is shown in execution order with its source. Each section header
carries the file path; each fenced block carries the file contents as captured
when this snapshot was generated. Use `Ctrl-F` against a path to find a script.

> **Snapshot, not a live mirror.** This bundle is a curated point-in-time copy
> for offline reading. The authoritative, always-current source is the repo
> itself — `automation/*.sh`, `tools/`, `Containerfile`, `Justfile`, and the
> `mios.toml` SSOT. If a fenced block here disagrees with the on-disk file,
> the on-disk file wins. Notable post-snapshot deltas are flagged inline.

---

=== BLOCK 2: inside embedded automation/build.sh — script classification (now matches current build.sh) ===
# ── Script classification ────────────────────────────────────────────────────
CONTAINERFILE_SCRIPTS="08-system-files-overlay.sh 99-postcheck.sh"

NON_FATAL_SCRIPTS="
  05-enable-external-repos.sh
  10-gnome.sh
  13-ceph-k3s.sh
  19-k3s-selinux.sh
  21-moby-engine.sh
  23-uki-render.sh
  36-akmod-guards.sh
  37-aichat.sh
  38-oh-my-posh.sh
  40-flatpak-bake.sh
  42-cosign-policy.sh
  43-uupd-installer.sh
  52-bake-kvmfr.sh
  53-bake-lookingglass-client.sh
  22-freeipa-client.sh
  26-gnome-remote-desktop.sh
  38-vm-gating.sh
  44-podman-machine-compat.sh
  50-enable-log-copy-service.sh
  91-strip-build-toolchain.sh
"

=== BLOCK 3: inside embedded install.ps1 Get-Hardware — annotated stale $aiModel line ===
    $baseImage = if ($hasNvidia) { "ghcr.io/ublue-os/ucore-hci:stable-nvidia" } else { "ghcr.io/ublue-os/ucore-hci:stable" }
    # NOTE (post-snapshot): the current install.ps1 no longer picks an Ollama model
    # tag here. Inference is the mios-llm-light lane (:11450); its model roster is
    # declared in usr/share/mios/llamacpp/llama-swap.yaml, not selected by RAM at
    # install time. This line is retained from the historical installer.
    $aiModel   = if ($ramGB -ge 32) { "qwen2.5-coder:14b" } elseif ($ramGB -ge 12) { "qwen2.5-coder:7b" } else { "phi4-mini:3.8b-q4_K_M" }

=== BLOCK 4: replaces the entire old `### automation/37-ollama-prep.sh` section + its fenced bash body ===
### `automation/37-ollama-prep.sh` — REMOVED (inference no longer uses Ollama)

> **Removed from the pipeline.** This script previously baked Ollama models into
> the image at build time. Ollama has been fully removed from MiOS — the binary,
> the `mios-ollama`/`mios-ollama-cpu` units, the Modelfiles, the CLI shim, and
> this `37-ollama-prep` model-bake step are all gone. Local inference and
> embeddings now run on the **`mios-llm-light`** lane (llama.cpp behind the
> upstream `llama-swap` proxy image, `ghcr.io/mostlygeek/llama-swap`) on
> **`:11450`**, which serves the everyday models, the `mios-opencode` coder model,
> and embeddings (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`). Its model
> roster is configured declaratively in `usr/share/mios/llamacpp/llama-swap.yaml`
> and prepared by `automation/38-llamacpp-prep.sh`; the gated heavy lanes are
> `mios-llm-heavy` (SGLang, `:11441`) and `mios-llm-heavy-alt` (vLLM). The engines
> speak the OpenAI/Ollama-compatible API, so "Ollama" survives only as that
> *upstream API-compat reference* — not as a live MiOS backend. The section is
> retained as a marker so older references to it resolve.

=== BLOCK 5: replaces the closing "## Skipped" + bundle-stats footer ===
## Skipped (not found at expected paths when this snapshot was generated)

- `preflight.sh`

## Pipeline scripts added after this snapshot (read from the repo)

The numbered pipeline has grown since this bundle was captured. The following
`automation/NN-*.sh` scripts exist in the current repo but are **not** embedded
above — read them directly from `automation/` (the live SSOT). They are listed
in execution order so the dependency ordering is still legible:

- `09-fonts.sh`
- `15-render-quadlets.sh` — renders Quadlet placeholders from `mios.toml`/`install.env`
- `34-sshd-port.sh`
- `38-hermes-agent.sh` — stages the MiOS-Hermes OpenAI-compat agent gateway (`:8642`)
- `38-llamacpp-prep.sh` — prepares the `mios-llm-light` llama.cpp lane (`:11450`)
- `38-oh-my-posh.sh`
- `38-vllm-prep.sh` — prepares the gated `mios-llm-heavy-alt` (vLLM) lane
- `39-opencode.sh` — stages the `mios-opencode` coder model + opencode gateway (`:8633`)
- `40-flatpak-bake.sh`
- `41-gpu-cdi-toolkits.sh`
- `41-mios-dropin-fanout.sh`
- `91-strip-build-toolchain.sh` — strips build-only toolchain from the final image

Conversely, `automation/37-ollama-prep.sh` and `automation/37-aichat.sh` were
removed from the repo; the `37-ollama-prep.sh` section above is retained only as
a "removed" marker, and `build.sh` still tolerates a missing `37-aichat.sh` via
its `NON_FATAL_SCRIPTS` list.

---


**Bundle stats:** point-in-time snapshot of the build-script source set. Treat
the repo (`automation/*.sh`, `tools/`, `Containerfile`, `Justfile`) as the
current source of truth; regenerate this bundle to refresh it.

=== END OF AUTHORED/CHANGED BLOCKS ===
All remaining content (Layer 1–4k verbatim build-script sources: bootstrap.sh/.ps1, install.sh/.ps1, build-mios.sh, Containerfile, Justfile, mios-build-local.ps1, the lib/*.sh helpers, every other automation/NN-*.sh body, ai-bootstrap.sh, etc.) is preserved unchanged on disk between these blocks.

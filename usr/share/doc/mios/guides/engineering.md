<!-- AI-hint: Defines the MiOS engineering standards — the 5-phase deployment pipeline, the `automation/` build sub-phase execution order, the `mios.toml` package-management schema, and the build-time conventions (shell, Containerfile, kargs, SELinux, service gating, AI-integration) that produce the immutable bootc/OCI image.
     AI-related: /usr/share/mios/mios.toml, /usr/share/mios/memory/v1.jsonl, mios-bootstrap, mios-ci, MIOS_AI_ENDPOINT -->
# 'MiOS' Engineering Standards

## Purpose of this guide

MiOS is an immutable, container-image-shaped Fedora workstation that *also*
ships as a local, self-replicating agentic AI OS: the whole operating system is
one `bootc`/OCI image you upgrade like a container and roll back like a Ctrl-Z.
This guide is the **build-pipeline rulebook** — the standards that govern how the
repo (whose root *is* the deployed system root) is compiled into that image and
how every script, package, and unit inside it must behave.

It sits one layer below the system's runtime behaviour: the conventions here
produce the artifact that the [deploy guide](deploy.md) then manages over its
`bootc` lifecycle, that the [self-build guide](self-build.md) reproduces across
CI/Linux/Windows, and that boots into the local AI surface documented in the
[API reference](../reference/api.md). Everything in MiOS — the inference lanes,
the agent orchestration, the security posture — exists *inside* the image these
rules build, so getting the build right is what makes the rest dependable.

Audience: contributors and CI authors adding or editing `automation/` scripts,
packages, Quadlets, and image policy. The non-negotiable contract is the six
**Architectural Laws** (see below and `CLAUDE.md`); everything else is the
craft of obeying them.

## Global pipeline phases

The end-to-end pipeline (bootstrap → install) is partitioned into five phases.
The numbered `automation/[0-9][0-9]-*.sh` scripts are *sub-phases* of Phase-2
(build). This is how a clone of the repo becomes a booting image:

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap.git/install.sh` | Preflight + profile load + identity capture |
| Phase-1 | `mios-bootstrap.git/install.sh` | Total Root Merge of `mios.git` and `mios-bootstrap.git` to `/` |
| Phase-2 | `Containerfile`/`automation/build.sh` | Build the running system (this section's subject) |
| Phase-3 | `mios.git/install.sh` + bootstrap profile staging | systemd-sysusers/tmpfiles/daemon-reload + user create + per-user `~/.config/mios/{profile.toml,system-prompt.md}` |
| Phase-4 | `mios-bootstrap.git/install.sh` | Reboot prompt |

The output of Phase-2 is a single OCI image (default ref
`ghcr.io/mios-dev/mios:latest`). Because `/usr` is a read-only composefs mount,
`/etc` gets a 3-way merge, and `/var` survives upgrades, the build rules below
exist to keep those guarantees true — most of them are direct consequences of
the Architectural Laws.

## Phase-2: build pipeline (sub-phases)

`Containerfile` triggers `automation/build.sh`, which iterates every
`automation/[0-9][0-9]-*.sh` in numeric order. Two scripts are skipped by the
orchestrator: `08-system-files-overlay.sh` (runs pre-pipeline directly from the
`Containerfile`'s main `RUN`) and the CI-skipped model-bake sub-phase in the
`37-*` range. Sub-phase numbering encodes dependency order and must be preserved
when adding new scripts. See `CLAUDE.md` for the sub-phase ranges.

> **Inference note.** MiOS no longer bakes or runs Ollama. Local inference and
> embeddings are served by `mios-llm-light` (llama.cpp behind the upstream
> llama-swap proxy image, `:11450`), with optional heavy GPU lanes (`mios-llm-heavy`,
> SGLang `:11441`; `mios-llm-heavy-alt`, vLLM). Any historical "ollama-prep"
> model-bake step is retired — model provisioning now targets the
> GGUF map at `usr/share/mios/llamacpp/mios-llm-light.yaml`.

Per-phase error handling: `automation/build.sh:234-237` toggles `set +e` around
each script invocation so individual failures are captured in
`FAIL_LOG`/`WARN_LOG` instead of aborting the orchestrator. Critical packages
declared in `usr/share/mios/mios.toml` under `[packages.critical].pkgs` are
post-validated via `rpm -q` (`automation/build.sh:285-300`).

## Package management

Single source of truth: `usr/share/mios/mios.toml`. Every RPM installed into the
image must live in a section under `[packages.<category>].pkgs`, parsed by
`automation/lib/packages.sh:get_packages`. Never call `dnf install` on
hard-coded names — that bypasses the SSOT and the audit. Human-readable rationale
documentation lives at `usr/share/doc/mios/reference/PACKAGES.md` (documentation,
not the runtime SSOT). Helpers:

- `install_packages "<category>"` -- best-effort, `--skip-unavailable`.
- `install_packages_strict "<category>"` -- fails the script on any miss.
- `install_packages_optional "<category>"` -- pure best-effort, never fails.

The `Containerfile` pre-pipeline `RUN` installs `packages-base` (security stack)
before `automation/build.sh` runs.

## Shell conventions

- `set -euo pipefail` at the top of every phase script.
- `VAR=$((VAR + 1))` for arithmetic. `((VAR++))` is forbidden -- under `set -e`
  it exits 1 when the result is 0.
- shellcheck-clean. SC2038 is fatal in CI (`.github/workflows/mios-ci.yml`).
- File names: `NN-name.sh` where NN encodes execution order.

## Containerfile conventions

- `ctx` stage holds the build context; the main stage bind-mounts `/ctx`
  read-only and writes mutable copies to `/tmp/build` (`Containerfile`).
- CRLF → LF normalization runs over all text files before any script executes
  (Windows build hosts leak CRLFs past `.gitattributes`).
- Final `RUN bootc container lint` (LAW 4).
- No `--squash-all` -- strips OCI metadata (`ostree.final-diffid`) bootc/BIB need.
- Kernel rule: only add `kernel-modules-extra`, `kernel-devel`, `kernel-headers`,
  `kernel-tools`. Never upgrade `kernel`/`kernel-core` in-container --
  `automation/01-repos.sh:65,68` excludes them explicitly.
- dnf option: `install_weak_deps=False` (underscore). `install_weakdeps` is
  silently ignored by dnf5.

## Kargs format

`usr/lib/bootc/kargs.d/*.toml` uses a flat top-level array:

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]
```

No `[kargs]` section header. No `delete` sub-key. bootc rejects anything else
(<https://bootc-dev.github.io/bootc/man/bootc-edit.html>).

## SELinux

Custom policies are split into per-rule `.te` modules in
`usr/share/selinux/packages/mios/` (compiled and shipped, not loaded at build
time -- see `automation/19-k3s-selinux.sh:46-51`). New booleans and fcontexts are
declared via `semanage` calls in `automation/37-selinux.sh`.

## Service gating

Quadlet sidecars and host services are gated by environment so the same image
boots correctly on bare metal, in a VM, or under WSL2:

- Bare-metal-only services: `ConditionVirtualization=no` drop-in.
- WSL2-incompatible services: `ConditionVirtualization=!wsl`.
- Optional services: `systemctl enable ... || true`.

## AI integration patterns

The local agent stack is the reason MiOS is more than a hardened desktop: a
build that wires the AI surface correctly produces a machine where every agent
and tool talks to one brain.

- **Unified endpoint (LAW 5).** All system agents target the OpenAI-v1 protocol
  at `MIOS_AI_ENDPOINT` (default `http://localhost:8080/v1`). Vendor-hardcoded
  URLs are forbidden. Behind that single redirect sits the agent stack:
  the agent-pipe (`:8640`) → the MiOS-Hermes gateway (`:8642`, sessions /
  tool-calling / skills) → the inference lanes (`mios-llm-light` on `:11450`
  for everyday models *and* embeddings via `nomic-embed-text`/`/v1/embeddings`;
  the gated heavy lanes `mios-llm-heavy` SGLang `:11441` and `mios-llm-heavy-alt`
  vLLM). The prefilter (`:8641`), Open WebUI front-end (`:3030`), and SearXNG
  search (`:8888`) round out the surface. The point of LAW 5 is that any
  OpenAI-API-compatible client speaks to this whole chain without knowing which
  lane answered.
- **Persistent agent state.** The unified agent datastore is PostgreSQL +
  pgvector (`mios-pgvector` container, `:5432`); pgvector is the vector store for
  RAG/recall, and the schema (`usr/share/mios/postgres/schema-init.sql`) carries
  the agent_memory, event, tool_call, session, skill, knowledge, sys_env, and
  related tables.
- **Episodic journal:** `/usr/share/mios/memory/v1.jsonl` is seeded into
  `/var/lib/mios/memory/journal/` via `usr/lib/tmpfiles.d/mios.conf`.
- **Declarative state only:** `tmpfiles.d` and `sysusers.d` create every `/var`
  path and UID (LAW 2 — never `mkdir` in `/var` at build time).

These engines speak the OpenAI- and Ollama-compatible API, and the mios-llm-light
proxy is the upstream image (`ghcr.io/mostlygeek/llama-swap`) — those are
external API/tool references, not MiOS-internal Ollama backends.

## Upstream base image constraints (bootc)

`bootc container lint` (LAW 4) enforces at build time:
- Kernel present and detectable at `/usr/lib/modules/<kver>/vmlinuz`
- No files written under `/var` or `/run` in image layers -- these are
  runtime-mutable and never part of the composefs rootfs
- `/usr` structurally valid (no dangling symlinks, no unexpected setuid files)
- OCI config has `architecture` and `os` fields set
- `systemd` must be PID 1 (init at `/sbin/init`)

kargs.d constraint (also enforced by lint): flat `kargs = [...]` TOML array only.
No `[kargs]` section header, no `delete` sub-key. Files processed in lexicographic
order; earlier entries cannot be removed by later files in the same image -- use
runtime `bootc kargs --delete` for removal.

## Toolchain

The image lifecycle — build, sign, ship, install, upgrade, roll back — runs on a
small, stable set of tools:

| Tool | Use |
|---|---|
| `bootc` | Transactional system upgrade/rollback |
| `podman` | Quadlet sidecar orchestration (LAW 6: unprivileged Quadlets) |
| `bootc-image-builder` (BIB) | RAW/ISO/QCOW2/VHD/WSL2 disk images |
| `syft` | CycloneDX/SPDX SBOM (`automation/90-generate-sbom.sh`) |
| `cosign` | Keyless image signing in CI |
| `just` | Linux build orchestrator (`Justfile`) |

## Architectural Laws (the load-bearing contract)

Every contribution obeys these, enforced by build-time lint and
`automation/99-postcheck.sh`:

1. **USR-OVER-ETC** — static config in `/usr/lib/<component>.d/`; `/etc/` is
   admin-override only.
2. **NO-MKDIR-IN-VAR** — every `/var/` path declared via
   `usr/lib/tmpfiles.d/*.conf`; never written at build time.
3. **BOUND-IMAGES** — every Quadlet image symlinked into
   `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage`
   so it ships *with* the host.
4. **BOOTC-CONTAINER-LINT** — final `RUN` of the `Containerfile`. Fail the lint,
   fail the build.
5. **UNIFIED-AI-REDIRECTS** — every agent and tool targets `MIOS_AI_ENDPOINT`
   (`http://localhost:8080/v1`). No vendor-hardcoded URLs.
6. **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`,
   `Delegate=yes`. Documented exceptions (rationale in their headers):
   `mios-ceph`, `mios-k3s`, `mios-forgejo-runner`.

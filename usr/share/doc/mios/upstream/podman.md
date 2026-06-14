<!-- AI-hint: Documentation for Podman, Buildah, Skopeo, and Quadlet integration in MiOS — defines the bootc image build invariants, multi-arch manifest rules, and the systemd-podman bridge that orchestrates every image-delivered service across the agent, inference, storage, and cluster planes.
     AI-related: mios-build-local, mios-builder, mios-ceph, mios-k3s, mios-forgejo-runner, mios-llm-light, mios-pgvector, mios-ceph.container, mios-llm-light.container, mios-forgejo-runner.container -->
# Podman, Buildah, Skopeo, Quadlets

> **Where this fits.** MiOS is one OS built two ways at once: an immutable
> bootc/OCI-shaped Fedora workstation (the whole system is a single container
> image — boot it, `bootc upgrade` it like a `git pull`, `bootc rollback` it
> like a Ctrl-Z) that is *also* a local, self-replicating agentic AI OS.
> **Podman is the engine that makes both halves real.** It is the tool that
> *builds* that single image (`podman build` from `Justfile:build`), and — via
> Quadlets — the tool that *runs* every image-delivered service inside it: the
> inference lanes, the agent pipeline, the pgvector memory, the cluster and
> security sidecars. This doc is the contract for both jobs: the build
> invariants the image must satisfy so the bootc lifecycle can carry it forward,
> and the Quadlet conventions that keep every sidecar least-privileged and
> bound to the image.

> Used in MiOS for: image build (`podman build` from `Justfile:build`),
> sidecar orchestration (Quadlet units in `usr/share/containers/systemd/` —
> vendor — and `etc/containers/systemd/` — host override), and the Windows
> builder (`mios-build-local.ps1` creates a rootful `mios-builder` Podman
> machine).

## Projects

- Podman: <https://github.com/containers/podman> · docs <https://docs.podman.io/>
- buildah: <https://github.com/containers/buildah>
- skopeo: <https://github.com/containers/skopeo>
- Quadlet (systemd integration): <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>

## Half 1 — Podman as the image builder

The deliverable of a MiOS build is the OCI image (and, optionally, the disk
artifacts cut from it). `podman build` assembles the repo root (`usr/`, `etc/`,
`srv/`, `var/`) into that single image, the final `RUN bootc container lint`
gates it, and a host `bootc switch`/`upgrade` then deploys it while
`bootc rollback` reverts it. The invariants below are what keep that lifecycle
reproducible, atomic, and self-contained.

### Build invariants for bootc images

| Rule | Why | Where |
| --- | --- | --- |
| **No `--squash-all`** | Strips OCI metadata bootc needs (`ostree.final-diffid`); breaks layer reuse for `bootc upgrade` deltas and BIB disk-image cutting | `usr/share/doc/mios/guides/engineering.md` §Containerfile-conventions |
| `--no-cache` for production builds | Predictable, reproducible | `Justfile:build` and `mios-build-local.ps1` |
| Bind-mount build context | Keep `/ctx` read-only, mutate at `/tmp/build` | `Containerfile` `ctx` scratch stage |
| BuildKit cache mounts for dnf | 5–10× faster rebuilds without layer bloat | `Containerfile` `--mount=type=cache,...` |
| Multi-arch via `podman manifest` | `manifest create` + `manifest add` + `manifest push --all` | future `mios_build` `platforms` parameter |

`skopeo` and `buildah` are the lower-level halves of the same toolchain:
`buildah` is the build backend Podman drives, and `skopeo` is used to inspect,
copy, and push images between the local `containers-storage`, GHCR, and the
self-hosted Forgejo registry without a running daemon.

## Half 2 — Quadlets: the systemd-podman bridge

A Quadlet is a systemd unit that Podman generates from a `.container`,
`.volume`, `.network`, or `.kube` file. **MiOS uses Quadlets for every
image-delivered service** — there is no `docker compose`, no pet daemons. Each
sidecar is a declarative unit baked into the image, started by systemd, and
version-locked to the OS it shipped with. This is what makes the AI and cluster
planes part of the immutable OS rather than a pile of hand-installed services.

- Vendor-shipped Quadlets: `usr/share/containers/systemd/` (Law 1 — USR-OVER-ETC)
- Host-overridable Quadlets: `etc/containers/systemd/` (admin override only)

The services these Quadlets deliver span the whole system:

| Plane | Representative Quadlet units |
| --- | --- |
| Inference lanes | `mios-llm-light` (:11450, primary — llama.cpp behind the upstream llama-swap proxy image; everyday models + embeddings), `mios-llm-heavy` (:11441, SGLang), `mios-llm-heavy-alt` (vLLM), `mios-llm-worker@` (swarm workers) |
| Agent / front-end | `mios-open-webui` (:3030), `mios-searxng` (:8888) |
| Memory / storage | `mios-pgvector` (:5432, PostgreSQL + pgvector — the unified agent datastore), `mios-ceph` |
| Cluster / CI | `mios-k3s`, `mios-forge`, `mios-forgejo-runner` |
| Security / web tools | `mios-adguard`, `mios-crowdsec-dashboard`, `mios-webtools-*` |
| Remote access | `mios-guacd`, `mios-guacamole`, `mios-guacamole-postgres`, `mios-cockpit-link` |

> **Naming note.** Every shipped artifact is `mios-<component>` (lowercase
> kebab). The retired `CloudWS` project name became `mios-*` throughout
> (e.g. `mios-guacamole`, `mios-pxe-hub`, `mios-crowdsec-dashboard`).
> `mios-llm-light` (the upstream proxy image `ghcr.io/mostlygeek/llama-swap`) and
> the OpenAI/Ollama-compatible API are legitimate upstream references and are
> kept; only the MiOS *unit identity* is renamed (e.g. the primary inference
> lane is `mios-llm-light`, not an Ollama/`mios-mios-llm-light` unit).

### LAW 6 — UNPRIVILEGED-QUADLETS

Every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented
exceptions — each justified in its unit header — run as `User=root` / uid 0:

- `mios-ceph` — Ceph requires privileged storage access (uid 0).
- `mios-k3s` — needs full kernel namespaces + eBPF.
- `mios-forgejo-runner` — must run `podman build` against `/Containerfile` and
  write to the rootful `/var/lib/containers/storage/` so the built image is
  usable by `bootc switch --transport containers-storage`. The runner's
  *job sandbox* (an ephemeral per-workflow container) is what protects the host,
  not the runner itself.

### LAW 3 — BOUND-IMAGES

Every Quadlet image is symlinked into `/usr/lib/bootc/bound-images.d/` and baked
into `/usr/lib/containers/storage` at build time, so `bootc upgrade` pulls/caches
each sidecar image alongside the OS image — the services arrive atomically with
the OS, never as a separate online fetch. Binder loop:
`automation/08-system-files-overlay.sh:74-86`.

### Service gating (defaults policy)

Every service boolean ships `true`. Disablement happens via systemd
`Condition*` directives in the Quadlet/unit, not via static config — so a unit
that can't run on a given host (no cluster, nested container, no GPU) skips
cleanly at pre-boot rather than crash-looping:

```ini
# usr/share/containers/systemd/mios-ceph.container excerpt
[Unit]
ConditionPathExists=/etc/ceph/ceph.conf
ConditionVirtualization=!container

[Container]
User=root          # documented exception to LAW 6
Group=root

[Service]
Delegate=yes
```

The gated heavy inference lanes (`mios-llm-heavy`, `mios-llm-heavy-alt`) follow
the same pattern: present in the image, inert until enabled in `mios.toml` and
reachable (`health_gate`), because they contend for the dGPU's VRAM.

## Windows builder (`mios-build-local.ps1`)

The 5-phase Windows orchestrator creates a rootful Podman Desktop machine named
`mios-builder` with all CPU cores, all RAM, and a 250 GB disk. After
`podman build` completes (followed by rechunk, disk-image cutting, and the
optional GHCR push), the script restores the previous default machine. This is
the Windows-host path to producing the same OCI image the Linux `just build`
pipeline produces.

## Cross-refs

- `usr/share/doc/mios/concepts/architecture.md` — system architecture, the six
  Architectural Laws, the build-pipeline phases, and the AI surface.
- `usr/share/doc/mios/guides/engineering.md` — Containerfile conventions and the
  no-`--squash-all` rationale.
- `usr/share/doc/mios/reference/api.md` — the OpenAI-compatible AI surface the
  inference-lane Quadlets serve.
- `usr/share/containers/systemd/mios-llm-light.container` — the primary
  inference Quadlet (was the Ollama/LocalAI unit; now llama.cpp via the
  upstream llama-swap proxy image on :11450).

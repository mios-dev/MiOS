<!-- AI-hint: Documentation for the GitHub Container Registry (GHCR) integration — the distribution endpoint for the single MiOS OCI image and the AI/quadlet images bound into it. Covers image paths, CI/user/bootc auth, multi-arch manifest handling, and retention policy.
     AI-related: mios-dev, ghcr.io/mios-dev/mios, ghcr.io/ublue-os/ucore-hci, ghcr.io/mostlygeek/llama-swap -->
# GitHub Container Registry (GHCR)

> **Why this matters to MiOS.** MiOS is *one whole system shipped as one OCI
> image*: an immutable bootc/OCI Fedora workstation that is also a local,
> self-replicating agentic AI OS. GHCR is the registry where that image lives,
> so it is the seam between the two halves of MiOS's lifecycle — **build
> pipeline → OCI image → bootc lifecycle on the host.** A host runs
> `bootc switch`/`bootc upgrade` against a GHCR ref the way you'd `git pull`;
> `bootc rollback` is the Ctrl-Z. Because the entire OS (GNOME/Wayland, the
> GPU/virt/cluster stack, *and* the local agent plane) is baked into that single
> ref, GHCR is also how MiOS "re-creates itself": every box that pulls the ref
> reproduces the same version-locked system, agent stack included.

> MiOS images live at `ghcr.io/mios-dev/mios:*`. CI publishes with
> `GITHUB_TOKEN` (`packages: write` permission); hosts and `bootc` pull them.

- Docs: <https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry>

## Auth

GHCR uses GitHub credentials. The credential differs by context:

| Context | Credential |
| --- | --- |
| CI (GitHub Actions) | `GITHUB_TOKEN` with `packages: write` (granted in the workflow `permissions:` block) |
| End user | GitHub PAT with `read:packages` (anonymous pull works for public packages) |
| `bootc switch` / `bootc upgrade` | Anonymous pull works for public images; for private packages, configure `/etc/containers/auth.json` |

The `bootc` row is the load-bearing one for day-to-day MiOS: the host pulls the
production image directly from GHCR to deploy or upgrade. No build host,
package manager, or vendor account sits in that path.

## Multi-arch

GHCR supports OCI manifest lists, so one ref can resolve to per-architecture
images. MiOS currently ships **amd64 only** (the workstation's NVIDIA + AMD
ROCm + Intel iGPU stack and the bound AI/quadlet images target x86_64); the
build tooling's `platforms` parameter accepts `linux/arm64` for forward compat.
Publish a manifest list with:

```bash
podman manifest create ghcr.io/mios-dev/mios:latest
podman manifest add  ghcr.io/mios-dev/mios:latest containers-storage:localhost/mios:amd64
podman manifest add  ghcr.io/mios-dev/mios:latest containers-storage:localhost/mios:arm64
podman manifest push --all ghcr.io/mios-dev/mios:latest
```

## Retention (MiOS policy)

Because a published ref is a deployable, rollback-able system state, the
production digests must not be garbage-collected out from under a host:

- Latest signed `:latest` digest — protected
- Last 5 release-tag digests — protected (preserves `bootc rollback` targets)
- Untagged manifests — pruned at 90 days (GHCR default)

Configure protection via the GitHub package's "Manage Actions access" and
"Manage versions" UI, or via the REST API.

## Image refs MiOS uses

The MiOS image is built *from* one GHCR base, published *to* one GHCR repo, and
bakes in (Architectural Law 3, BOUND-IMAGES) the quadlet/AI images its services
need — including the GHCR-hosted upstream llama-swap proxy that fronts the
primary inference lane (`mios-llm-light`). So GHCR appears at three points in the
lifecycle: input base,
build-time bound images, and the published output.

| Ref | Purpose |
| --- | --- |
| `ghcr.io/mios-dev/mios:latest` | Production image — `bootc switch`/`bootc upgrade` target |
| `ghcr.io/mios-dev/mios:v0.3.0` | Pinned release (current `VERSION`) |
| `ghcr.io/mios-dev/mios@sha256:…` | Digest-pinned (most reproducible/secure) |
| `localhost/mios:latest` | Local build target (`MIOS_LOCAL_TAG`, `Justfile`) |
| `ghcr.io/ublue-os/ucore-hci:stable-nvidia` | Upstream base image (`MIOS_BASE_IMAGE`, `Justfile`) |
| `ghcr.io/mostlygeek/llama-swap:cuda` | Upstream proxy image fronting `mios-llm-light` (`:11450`); bound into the MiOS image per Law 3 |
| `quay.io/centos-bootc/bootc-image-builder:latest` | BIB — cuts disk artifacts from the image (`MIOS_BIB_IMAGE`, `Justfile`; Quay, not GHCR) |
| `anchore/syft:latest` | SBOM generator (`just sbom`; Docker Hub, not GHCR) |

The base, BIB, and `mios-llm-light` images are legitimate **upstream** references —
the inference engines speak the OpenAI/Ollama-compatible API and `mios-llm-light`
is the upstream proxy tool — kept as-is; only MiOS's *own* unit/service identity
follows the `mios-<component>` naming convention.

## Cross-refs

- [`usr/share/doc/mios/guides/self-build.md`](../guides/self-build.md) — build/CI modes and image publishing
- [`usr/share/doc/mios/reference/maturity-and-release-runbook.md`](../reference/maturity-and-release-runbook.md) — release tagging + signing
- [`usr/share/doc/mios/upstream/cosign.md`](cosign.md) — image signing / verification
- [`usr/share/doc/mios/guides/deploy.md`](../guides/deploy.md) — bootc switch/upgrade/rollback against a GHCR ref

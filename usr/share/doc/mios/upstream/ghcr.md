# GitHub Container Registry (GHCR)

> 'MiOS' images live at `ghcr.io/mios-dev/mios:*`. CI uses
> `GITHUB_TOKEN` with `packages: write` permission.

- Docs: <https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry>

## Auth

| Context | Credential |
| --- | --- |
| CI (GitHub Actions) | `GITHUB_TOKEN` with `packages: write` (granted in workflow `permissions:` block) |
| End user | GitHub PAT with `read:packages` (anonymous pull works for public packages) |
| `bootc switch` | Anonymous pull works; for private packages, configure `/etc/containers/auth.json` |

## Multi-arch

GHCR supports OCI manifest lists. 'MiOS' currently ships amd64 only;
the `mios_build` tool's `platforms` parameter accepts `linux/arm64` for
forward compat. Push with:

```bash
podman manifest create ghcr.io/mios-dev/mios:latest
podman manifest add  ghcr.io/mios-dev/mios:latest containers-storage:localhost/mios:amd64
podman manifest add  ghcr.io/mios-dev/mios:latest containers-storage:localhost/mios:arm64
podman manifest push --all ghcr.io/mios-dev/mios:latest
```

## Retention ('MiOS' policy)

- Latest signed `:latest` digest — protected
- Last 5 release-tag digests — protected
- Untagged manifests — pruned at 90 days (GHCR default)

Configure protection via the GitHub package's "Manage Actions access"
and "Manage versions" UI, or via the REST API.

## Image refs 'MiOS' uses

| Ref | Purpose |
| --- | --- |
| `ghcr.io/mios-dev/mios:latest` | Production image — bootc switch target |
| `ghcr.io/mios-dev/mios:v0.2.2` | Pinned release |
| `ghcr.io/mios-dev/mios@sha256:…` | Digest-pinned (most secure) |
| `localhost/mios:latest` | `Justfile` local build target (`Justfile:13`) |
| `ghcr.io/ublue-os/ucore-hci:stable-nvidia` | Upstream base (`Justfile:45`) |
| `quay.io/centos-bootc/bootc-image-builder:latest` | BIB (`Justfile:14`) |
| `anchore/syft:latest` | SBOM generator (`Justfile:sbom`) |

## Cross-refs

- `usr/share/doc/mios/60-ci-signing.md`
- `usr/share/doc/mios/upstream/cosign.md`

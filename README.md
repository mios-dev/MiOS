# MiOS

> The deployed root-overlay tree of the MiOS immutable workstation OS.

**Version:** v0.1.5
**Architecture:** OCI-bootc + ostree composefs
**Base image:** `ghcr.io/ublue-os/ucore-hci:stable-nvidia`
**Published:** `ghcr.io/kabuki94/mios:latest`

---

## What this repo is

This repo's working tree maps directly onto the deployed root filesystem (`/`).
Each tracked directory corresponds 1:1 to its target path:

| Path in repo | Path on deployed host | Purpose |
|---|---|---|
| `usr/` | `/usr` | System binaries, libraries, units, manifests (read-only on bootc) |
| `etc/` | `/etc` | System configuration overlays (Quadlets, etc.) |
| `var/` | `/var` | State directory placeholders (declared via tmpfiles.d) |
| `v1/` | `/v1` | OpenAI-namespace AI gateway (models/MCP discovery) |
| `srv/` | `/srv` | Stateful workload mounts (e.g. `/srv/ai` for model weights) |

The `.gitignore` is an allow-list: `/*` and `.*` ignore everything, then
`!`-rules whitelist exactly the paths MiOS owns. Cloning this repo into `/`
on a host therefore produces a clean overlay merge with no collisions against
unrelated system content.

## What this repo is NOT

This repo does NOT contain build infrastructure. The `Containerfile`,
`Justfile`, `automation/`, `tools/`, `install.sh`, `build-mios.sh`,
`mios-build-local.ps1`, `push-to-github.ps1`, `preflight.ps1`, `.env.mios`,
`INDEX.md`, and the AI-agent metadata files all live in
[Kabuki94/MiOS-bootstrap](https://github.com/Kabuki94/MiOS-bootstrap).

The OCI image build flow is:

1. Bootstrap ignites onto a host root (or into a CI workspace), placing
   `Containerfile` + `automation/` + `tools/` at the canonical paths.
2. MiOS clones into the same root and overlays its tree (lossless additive merge).
3. `podman build -f Containerfile` synthesizes the final OCI image from the
   merged tree.
4. CI signs (cosign keyless), rechunks (`bootc-base-imagectl`), and pushes to
   `ghcr.io/kabuki94/mios:latest`.
5. Deployed hosts pull updates via `sudo bootc upgrade`.

## OpenAI-namespace AI gateway

The `/v1` tree exposes models, MCP servers, and other AI metadata under the
canonical OpenAI REST namespace. The Quadlet at
`etc/containers/systemd/mios-ai.container` runs LocalAI bound to `/v1` so
clients can hit `http://localhost:8080/v1/models` and have it resolved against
the on-disk discovery tree.

## License

Apache-2.0. See [LICENSE](https://github.com/Kabuki94/MiOS-bootstrap/blob/main/LICENSE)
in the bootstrap repo.

## Project resources

- Repository: https://github.com/Kabuki94/MiOS
- Build infrastructure: https://github.com/Kabuki94/MiOS-bootstrap
- Container registry: `ghcr.io/kabuki94/mios`

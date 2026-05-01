# MiOS — System Layer AI Entry Point

> Agent loading order: this file → `/usr/share/mios/ai/system.md` (full prompt) → `/etc/mios/ai/system-prompt.md` (host override) → `~/.config/mios/system-prompt.md` (user overlay)

MiOS is an immutable bootc-native Fedora workstation OS delivered as an OCI image. The repo root (`mios.git`) **is** the system root `/` — no separate workspace.

## What mios.git owns (build + system layer)

| Path | Purpose |
|---|---|
| `/Containerfile` | OCI image definition (bootc, `FROM quay.io/fedora/fedora-bootc:42`) |
| `/Justfile` | Build entry (`just build`, `just push`, `just clean`) |
| `/automation/` | 48 shell scripts for system configuration |
| `/usr/lib/systemd/` | 38 systemd units + 4 Quadlet container definitions |
| `/usr/lib/dracut.conf.d/` + `/usr/lib/karg.d/` | 14 kernel argument files |
| `/usr/share/mios/PACKAGES.md` | Package manifest (parsed by `automation/80-install-packages.sh`) |
| `/usr/share/mios/profile.toml` | Vendor-default profile (lowest precedence) |
| `/usr/share/mios/env.defaults` | Global `MIOS_*` env variable defaults |

## Global env surface

All `MIOS_*` variables resolve via five-layer cascade (highest wins):

```
$MIOS_VAR env → ~/.config/mios/env → /etc/mios/install.env → /etc/mios/env.overrides → /usr/share/mios/env.defaults
```

Key vars: `MIOS_AI_MODEL`, `MIOS_AI_EMBED_MODEL`, `MIOS_AI_BASE_URL`, `MIOS_BASE_IMAGE`, `MIOS_VERSION`

## Build pipeline

```
just build   # Containerfile → OCI image
just push    # push to ghcr.io/mios-dev/mios:latest
just clean   # prune local image cache
```

Local dev: `./mios-build-local.ps1` (Windows) · `./automation/build.sh` (Linux)

## Merge-at-build semantics

At `just build`, `mios-bootstrap.git` is fetched and merged onto this repo via `automation/00-bootstrap-merge.sh`. Bootstrap values (user profile, AI files, flatpak lists) override the vendor defaults in this repo. The merged result is baked into the OCI image.

## Six Architectural Laws

1. **USR-OVER-ETC** — defaults in `/usr/share/`; overrides in `/etc/`; never reverse
2. **NO-MKDIR-IN-VAR** — runtime dirs declared in `tmpfiles.d`, not `mkdir` in scripts
3. **BOUND-IMAGES** — all container images pinned; never `:latest` in Quadlets
4. **BOOTC-CONTAINER-LINT** — `RUN bootc container lint` is always the final Containerfile instruction
5. **UNIFIED-AI-REDIRECTS** — all `MIOS_AI_*` vars point to `http://localhost:8080/v1`; no vendor endpoints in committed files
6. **UNPRIVILEGED-QUADLETS** — all Quadlet containers run rootless unless security policy demands root

## Full agent context

Load `/usr/share/mios/ai/system.md` for the complete prompt covering all 48 automation scripts, 38 systemd units, 4 Quadlets, 14 karg files, user creation, profile resolution, and day-2 operations.

# MiOS — System Layer AI Entry Point

> Agent loading order: this file → `/usr/share/mios/ai/system.md` (full prompt) → `/etc/mios/ai/system-prompt.md` (host override) → `~/.config/mios/system-prompt.md` (user overlay)

MiOS is an immutable bootc-native Fedora workstation OS delivered as an OCI image. The repo root (`mios.git`) **is** the system root `/` — no separate workspace.

## What mios.git owns (build + system layer)

| Path | Purpose |
|---|---|
| `/Containerfile` | OCI image definition (bootc, FROM ucore-hci:stable) |
| `/Justfile` | Build entry (`just build`, `just rechunk`, `just iso`, etc.) |
| `/automation/` | 45 numbered phase scripts + lib/{common,packages,masking}.sh |
| `/usr/lib/systemd/system/` | systemd units + drop-ins |
| `/usr/lib/kargs.d/` | 14 kernel argument TOML files |
| `/usr/share/mios/PACKAGES.md` | SSOT for all RPM packages (fenced packages-<category> blocks) |
| `/usr/share/mios/profile.toml` | Vendor-default profile (lowest precedence) |
| `/usr/share/mios/env.defaults` | Global `MIOS_*` env variable defaults |

## Global env surface

All `MIOS_*` variables resolve via cascade (highest wins):

```
~/.config/mios/env > /etc/mios/install.env > /etc/mios/env.d/*.env > /usr/share/mios/env.defaults
```

Key vars: `MIOS_AI_ENDPOINT`, `MIOS_AI_MODEL`, `MIOS_AI_EMBED_MODEL`, `MIOS_AI_KEY`, `MIOS_BASE_IMAGE`, `MIOS_VERSION`

## Build pipeline

```
just build          # Containerfile → OCI image → localhost/mios:latest
just build-logged   # build with tee'd log
just rechunk        # bootc-base-imagectl rechunk (smaller Day-2 deltas)
just iso            # Anaconda installer ISO via bootc-image-builder
just wsl2           # WSL2 tar.gz for wsl --import
just sbom           # CycloneDX SBOM via syft
```

Single-phase iteration: `bash automation/<NN>-<name>.sh`

## Six Architectural Laws

1. **USR-OVER-ETC** — static config in `/usr/lib/<component>.d/`; `/etc/` for admin overrides only
2. **NO-MKDIR-IN-VAR** — every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`
3. **BOUND-IMAGES** — every Quadlet sidecar image symlinked in `/usr/lib/bootc/bound-images.d/`
4. **BOOTC-CONTAINER-LINT** — `RUN bootc container lint` is the final Containerfile instruction
5. **UNIFIED-AI-REDIRECTS** — `MIOS_AI_ENDPOINT/MODEL/KEY` target `http://localhost:8080/v1`; zero vendor URLs in committed files
6. **UNPRIVILEGED-QUADLETS** — every Quadlet defines `User=`, `Group=`, `Delegate=yes`; exceptions: `mios-k3s.container`, `mios-ceph.container`

## Full agent context

Load `/usr/share/mios/ai/system.md` for the complete prompt covering all automation scripts, systemd units, Quadlet sidecars, kernel args, user creation, profile resolution, and day-2 operations.

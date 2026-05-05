# bootc — Bootable Containers (CNCF Sandbox)

> Used by MiOS for: every host-state mutation. `Containerfile` produces
> a bootc image; `bootc upgrade`/`switch`/`rollback` is the only sanctioned
> way to mutate the deployed system. Source: `usr/share/doc/mios/concepts/architecture.md` §Pillars,
> `Containerfile` final RUN, `usr/share/doc/mios/guides/engineering.md` §Toolchain.

## What it is

bootc boots and upgrades a Linux host from an **OCI container image**.
The booted host today is backed by ostree (with composefs work in
progress as `bootc composefs-native`). MiOS is a bootc image —
`ghcr.io/mios-dev/mios:latest`.

- Project: <https://github.com/bootc-dev/bootc>
- Docs: <https://bootc-dev.github.io/bootc/> (canonical) and <https://bootc.dev/>
- Releases: <https://github.com/bootc-dev/bootc/releases>

## Key commands (used by MiOS)

| Command | Purpose | Used in MiOS |
| --- | --- | --- |
| `bootc status [--format=json]` | current deployment, kargs, image ref | `mios "what is the current image tag?"` agent verb |
| `bootc upgrade [--apply]` | pull newer revision of configured ref, stage (or apply+reboot) | end-user Day-2 |
| `bootc switch <imgref>` | change configured ref, then pull | end-user Day-2 |
| `bootc rollback` | revert to previous deployment | end-user Day-2 |
| `bootc kargs edit` / `--append` / `--delete` | runtime kargs editing | end-user override (SECURITY.md §Override-surfaces) |
| `bootc install to-disk` / `to-filesystem` | initial install (runs inside privileged container) | one-shot first-boot from BIB output |
| `bootc container lint` | validate an OCI image as a valid bootc image | **final RUN of MiOS Containerfile (LAW 4)** |
| `bootc-base-imagectl rechunk` | re-layer an image for smaller deltas | `just rechunk` (`automation/build.sh` invokes it) |

## Build-time invariants enforced by `bootc container lint`

These are the LAW-4 invariants. Violating any one fails the MiOS build:

- Kernel present and detectable at `/usr/lib/modules/<kver>/vmlinuz`
- No files written under `/var` or `/run` in image layers (these are
  runtime-mutable; declare via `usr/lib/tmpfiles.d/*.conf`)
- `/usr` structurally valid: no dangling symlinks, no unexpected setuid
- OCI config has `architecture` and `os` set
- `/sbin/init` is systemd PID 1
- kargs.d files use the flat `kargs = [...]` TOML format only

## Pre-flight free-space check

bootc 1.5+ does a pre-flight free-space check on `bootc upgrade` (#1995).
If `/sysroot` is full, `bootc rollback` (clear staged) or
`ostree admin undeploy <index>` (drop a pinned old deployment) frees space.

## Status output (MiOS contract)

The `bootc_status` function tool (`/usr/lib/mios/tools/responses-api/bootc_status.json`)
wraps `bootc status --format=json` so an agent can ask "what's the booted
image?" without parsing free-form output. See `mios.go` agent in
`mios-bootstrap` for the runtime caller.

## Cross-refs in MiOS

- `Containerfile` last `RUN bootc container lint`
- `Justfile` `lint` recipe re-runs lint on the locally-built tag
- `automation/build.sh` calls `bootc container lint` once more inside the
  build to fail fast (mirrored by the Containerfile's final RUN)
- `usr/share/doc/mios/guides/engineering.md` §Upstream-base-image-constraints lists every lint
  invariant
- `SECURITY.md` §Image-signing combines `bootc switch` with
  `cosign verify` for trusted boot

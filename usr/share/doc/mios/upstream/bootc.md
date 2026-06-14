<!-- AI-hint: Documentation for the bootc tool, which MiOS uses as the primary mechanism for host-state mutations, image-based deployments, and system upgrades via OCI images.
     AI-related: /usr/lib/mios/tools/responses-api/bootc_status.json, mios-dev, mios-bootstrap -->
# bootc — Bootable Containers (CNCF Sandbox)

> Used by MiOS for: every host-state mutation. `Containerfile` produces
> a bootc image; `bootc upgrade`/`switch`/`rollback` is the only sanctioned
> way to mutate the deployed system. Source: `usr/share/doc/mios/concepts/architecture.md` §Pillars,
> `Containerfile` final RUN, `usr/share/doc/mios/guides/engineering.md` §Toolchain.

## Why this matters to MiOS

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image) that is *also* a
**local, self-replicating, agentic AI operating system**. bootc is the
mechanism that makes that dual nature possible. The entire system — GNOME on
Wayland, the GPU/virtualization stack, *and* the local agent plane (inference
lanes, the agent-pipe/Hermes orchestrator, PostgreSQL+pgvector memory, the
MCP/A2A tool surface) — is baked into one OCI image. bootc boots that image,
`bootc upgrade`s it like a `git pull`, and `bootc rollback`s it like a Ctrl-Z.

That single-image discipline is what makes the AI half of MiOS trustworthy: the
agent stack isn't a pile of pip-installed daemons to babysit — it is
version-locked to the OS, ships *inside* the same immutable image (Architectural
Law 3, BOUND-IMAGES), and is reproduced exactly on every host that pulls the
ref. bootc is the lifecycle that carries that whole system forward atomically.
This document describes the tool itself and the exact contract MiOS holds it to.

## What it is

bootc boots and upgrades a Linux host from an **OCI container image**.
The booted host today is backed by ostree (with composefs work in
progress as `bootc composefs-native`). MiOS is a bootc image —
`ghcr.io/mios-dev/mios:latest`.

- Project: <https://github.com/bootc-dev/bootc>
- Docs: <https://bootc-dev.github.io/bootc/> (canonical) and <https://bootc.dev/>
- Releases: <https://github.com/bootc-dev/bootc/releases>

## Where it sits in the MiOS lifecycle

The system has a two-half lifecycle, and bootc owns the second half:

```
build pipeline (Containerfile + automation/NN-*.sh)  ─┐
   produces an OCI image                              │  bootc switch / upgrade
ghcr.io/mios-dev/mios:latest                          ├─►  deploys it to a host
   (GNOME + GPU/virt stack + full local agent plane)  │  bootc rollback
                                                       ┘     reverts it atomically
```

The build pipeline (see `usr/share/doc/mios/guides/engineering.md` §Toolchain)
assembles the image — including the numbered automation steps that stand up the
AI plane — and its final `RUN bootc container lint` is the gate that proves the
image is a valid bootc image before it can ship. On the host, `bootc` is the
*only* sanctioned way to change deployed system state.

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
| `bootc-base-imagectl rechunk` | re-layer an image for smaller deltas | `just rechunk` (`/usr/libexec/bootc-base-imagectl rechunk`) |

## Build-time invariants enforced by `bootc container lint`

These are the LAW-4 invariants. Violating any one fails the MiOS build:

- Kernel present and detectable at `/usr/lib/modules/<kver>/vmlinuz`
- No files written under `/var` or `/run` in image layers (these are
  runtime-mutable; declare via `usr/lib/tmpfiles.d/*.conf` — this is
  Architectural Law 2, NO-MKDIR-IN-VAR)
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
image?" without parsing free-form output. This is the bridge between the bootc
lifecycle and the agent plane: it lets MiOS reason about its own deployed
revision through the same OpenAI-compatible tool surface every other verb uses.
See the `mios.go` agent in `mios-bootstrap` for the runtime caller.

## Cross-refs in MiOS

- `Containerfile` last `RUN bootc container lint`
- `Justfile` `lint` recipe re-runs lint on the locally-built tag; `just rechunk`
  invokes `/usr/libexec/bootc-base-imagectl rechunk` for smaller Day-2 deltas
- `automation/build.sh` runs the numbered Phase-2 sub-phases; the Containerfile's
  final `RUN bootc container lint` fails the build fast on any violation
- `usr/share/doc/mios/guides/engineering.md` §Upstream base image constraints (bootc)
  lists every lint invariant
- `SECURITY.md` §Image-signing combines `bootc switch` with
  `cosign verify` for trusted boot

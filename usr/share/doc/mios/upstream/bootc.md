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
The booted host today is backed by ostree; a native composefs backend exists
behind `bootc install --composefs-backend` and is still marked experimental
upstream (see [Installing a bootc image](#installing-a-bootc-image)). MiOS is a bootc image —
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
| `bootc install to-disk` / `to-filesystem` / `to-existing-root` | initial install, run by the image's own bootc in a privileged container | `mios-install disk` / `mios-install existing-root` ([below](#installing-a-bootc-image)); BIB output |
| `bootc container lint` | validate an OCI image as a valid bootc image | **final RUN of MiOS Containerfile (LAW 4)** |
| `bootc-base-imagectl rechunk` | re-layer an image for smaller deltas | `just rechunk` (`/usr/libexec/bootc-base-imagectl rechunk`) |

## Installing a bootc image

Badges: **[verified]** names the primary source checked; **[unverified]** was
not confirmed from a primary source; **[inference]** is MiOS's reading.
Researched 2026-10-01; staging notes in
`.research/native-installer-bootc-prior-art-2026-10.md`.

**Versions in play.** The newest bootc tag is v1.16.14 (2026-09-23)
**[verified: <https://github.com/bootc-dev/bootc> tags]**; Fedora 44 ships
1.16.13 **[verified: `bootc --version` in a Fedora 44 container, 2026-10-01]**; the uCore base image release
`stable-20261001` carries 1.16.10 **[verified:
<https://github.com/ublue-os/ucore/releases/tag/stable-20261001>]**. The bootc
that installs MiOS is the one inside the image being installed, so the image's
version is the one whose flags count.

**Three legs** **[verified:
<https://github.com/bootc-dev/bootc/blob/v1.16.14/docs/src/bootc-install.md>,
`crates/lib/src/install.rs` at v1.16.14]**:

| Leg | What it does | MiOS entry point |
| --- | --- | --- |
| `to-disk DEV` | partitions and formats DEV (`--wipe` clears it first), deploys, installs the bootloader; `--via-loopback` targets a file | `mios-install disk` |
| `to-filesystem PATH` | deploys into filesystems something else partitioned and mounted | not yet in `mios-install` |
| `to-existing-root` | installs over the running system; `--replace=alongside` (default) keeps it running until reboot, `--cleanup` removes the old files at first boot | `mios-install existing-root` |

**Run it from the image.** The documented invocation runs bootc inside the
image being installed: `podman run --rm --privileged --pid=host -v /dev:/dev
-v /var/lib/containers:/var/lib/containers --security-opt
label=type:unconfined_t <image> bootc install …` **[verified: bootc-install.md
at v1.16.14]**. bootc then takes its source image from the running container.
Running the host's bootc with `--source-imgref` instead is outside that
envelope; bootc discussion #1400 reports SELinux-policy and
`prepare-root.conf` failures for it **[verified:
<https://github.com/bootc-dev/bootc/discussions/1400>]**, and issues #433 and
#879 remain open **[verified]**. `mios-install` also passes `--ipc=host`, as
the docs' flag set does.

**`to-existing-root` and `-v /:/target`.** The docs still mount the host root
at `/target`; the CLI help says the root path is "now not necessary to
provide" **[verified: `bootc install to-existing-root --help`, 1.16.13]**.
`mios-install` keeps the mount until the shorter form is tested on a MiOS host
**[inference]**.

**Install configuration** is TOML in
`{/usr/lib,/usr/local/lib,/etc,/run}/bootc/install/*.toml`, an `[install]`
table parsed with unknown keys rejected **[verified:
<https://github.com/bootc-dev/bootc/blob/v1.16.14/crates/lib/src/install/config.rs>]**.
The flat `root-fs-type` key is valid; when `install.filesystem.root.type` is
also set, that one wins **[verified: config.rs]**. MiOS generates
`usr/lib/bootc/install/00-mios.toml` from `[bootc_install]` in mios.toml.
Exactly which keys `bootc install print-configuration` prints is
**[unverified]**; check it inside the built image.

**Partitioning.** At v1.16.13 and v1.16.14, `to-disk` partitions with sfdisk;
the `systemd-repart` path that reads `/usr/lib/repart.d` exists on bootc's
main branch only **[verified: `crates/lib/src/install/baseline.rs`, 0
matches for systemd-repart at both tags]**. So `usr/lib/repart.d/50-root.conf`
does not shape a `to-disk` install with the bootc MiOS ships today
**[inference]**; partition sizes are controllable only by partitioning first
and using `to-filesystem`.

**Filesystems and flags** (1.16.13 `--help`, **[verified]**):
`--filesystem` accepts `xfs | ext4 | btrfs`; `--bound-images` is `stored`
(logically bound images must already be in the source's container storage,
the default) or `pull`; `--target-no-signature-verification` is now a no-op
and `--enforce-container-sigpolicy` is its inverse; `--target-imgref` names
the image the installed host tracks for `bootc upgrade`; `--source-imgref`
takes a skopeo-style reference such as `oci-archive:PATH`. There is no
`--transport` flag (the target side is `--target-transport`, default
`registry`).

**Composefs backend.** `--composefs-backend`, `--uki-addon` and
`--bootloader grub-cc` already exist in v1.16.10 through v1.16.14
**[verified]**; the backend is documented as experimental, and its on-disk
format may still change **[verified: bootc docs]**. MiOS stays on the ostree
backend **[inference]**.

**Bootloader on the uCore base.** That ucore-hci boots through bootupd, shim
and GRUB is **[unverified]**: the release notes do not list them. Check with
`rpm -q bootupd shim-x64` in the built image before relying on it.

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

- `tools/native/mios-install` -- the installer (`disk`, `existing-root`);
  `[bootc_install]` in mios.toml; ADR-0014

- `Containerfile` last `RUN bootc container lint`
- `Justfile` `lint` recipe re-runs lint on the locally-built tag; `just rechunk`
  invokes `/usr/libexec/bootc-base-imagectl rechunk` for smaller Day-2 deltas
- `automation/build.sh` runs the numbered Phase-2 sub-phases; the Containerfile's
  final `RUN bootc container lint` fails the build fast on any violation
- `usr/share/doc/mios/guides/engineering.md` §Upstream base image constraints (bootc)
  lists every lint invariant
- `SECURITY.md` §Image-signing combines `bootc switch` with
  `cosign verify` for trusted boot

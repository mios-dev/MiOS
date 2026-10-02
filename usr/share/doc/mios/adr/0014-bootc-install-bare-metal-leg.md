<!-- AI-hint: Architecture decision for installing MiOS onto hardware: the image's own bootc runs in podman via mios-install (to-disk, to-existing-root, to-filesystem). -->
<!-- AI-related: tools/native/mios-install, tools/install.sh, usr/share/doc/mios/upstream/bootc.md -->
---
adr: 0014
title: "The bootc-install bare-metal leg: the image's own bootc, run by mios-install"
status: accepted
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [bootc, bare-metal, installation, oci, offline]
laws: [3, 4, 12, 14]
ssot_keys: [image.ref, bootc_install]
related_ws: [WS-CAT, WS-MDRIVE]
supersedes: []
superseded_by: []
---

# ADR-0014: The bootc-install bare-metal leg: the image's own bootc, run by mios-install

## Status

Accepted — 2026-10-02 (proposed 2026-07-28). The operator chose to install
the MiOS image itself (`[image].ref`, which is built FROM the ucore-hci base)
and to run bootc inside that image through podman. All three legs are implemented: `disk` and `filesystem` (both
with the offline `oci-archive:` source) and `existing-root`.

## Context

MiOS is updated with `bootc upgrade`/`switch`/`rollback`, but blank hardware
needs an installer. bootc provides three install legs: `to-disk`,
`to-filesystem` and `to-existing-root`. The earlier draft of this ADR planned
`bootc install to-disk --transport oci`; bootc has no `--transport` flag. An
offline source is named with `--source-imgref oci-archive:PATH`, and the image
the installed host tracks is `--target-imgref` (`--target-transport` defaults
to `registry`). Upstream documents running bootc inside the image being
installed; host-run `--source-imgref` installs are outside that envelope
(bootc discussion #1400). Evidence, with sources:
`usr/share/doc/mios/upstream/bootc.md` §Installing a bootc image.

## Decision

1. **One installer: `mios-install`** (`tools/native/mios-install`, a Rust
   static-pie binary, Law 14). It owns disk discovery, the safety gates and
   the plan, and execs bootc; it does not link bootc, which depends on
   libostree, glib and OpenSSL.
2. **bootc runs from the image being installed:**
   `podman run --rm --privileged --pid=host --ipc=host -v /dev:/dev
   -v /var/lib/containers:/var/lib/containers
   --security-opt label=type:unconfined_t <[image].ref> bootc install …`.
3. **Legs:**
   - `mios-install disk` → `to-disk --wipe --bound-images <policy>
     [--filesystem F] DEV`; a disk backing the running system is always
     refused, as is one below `[bootc_install].root_min_gb`.
   - `mios-install existing-root` → `to-existing-root
     --acknowledge-destructive --bound-images <policy> [--cleanup]`, with
     the host root at `/target`.
   - `mios-install filesystem ROOT` → `to-filesystem --bound-images <policy>
     [--root-mount-spec S] [--boot-mount-spec S] [--skip-finalize] ROOT`,
     with ROOT mounted into the container at the same path; ROOT must be a
     mounted, empty filesystem other than `/`. This is the leg for
     partitioning chosen ahead of time (the only way to control partition
     sizes with the shipped bootc); driving `systemd-repart` from
     mios-install is future work.
4. **Configuration comes from mios.toml.** `[image].ref` is the image;
   `[bootc_install]` holds the root filesystem, the root-partition floor and
   padding, and the bound-images policy, and is projected into
   `usr/lib/bootc/install/00-mios.toml` and `usr/lib/repart.d/50-root.conf`.
5. **Offline installs** (USB/Ventoy, Law 12): `mios-install disk --source
   oci-archive:PATH` loads the staged archive with `podman load`, runs the
   image podman reports as loaded, and sets `--target-imgref` to
   `[image].ref`, so `bootc upgrade` follows the published image after
   install. `tools/install.sh` is the front end on the live media.

## Rationale

- Running the image's own bootc makes the installer's bootc the version the
  image was built and tested with, and is the configuration upstream
  documents and tests.
- A static binary that execs bootc keeps the native-tier rule (Law 14)
  without linking C libraries that cannot be built statically.
- One installer replaces the Python planner, which defaulted to the base
  image and passed a flag bootc does not accept.

## Alternatives

- **Host bootc with `--source-imgref`**: no podman dependency, but the host's
  bootc version decides the install and #1400 reports SELinux and
  `prepare-root.conf` failures.
- **Anaconda kickstart (`bootc`/`ostreecontainer`)**: cannot install
  logically bound images, and adds a second installer to maintain.
- **Linking bootc or ostree**: not possible as a static binary.

## Consequences

### Positive
- Bare-metal and in-place installs from one tested binary, with every
  tunable in mios.toml.
- The installed host tracks `[image].ref` for upgrades.

### Negative
- Requires podman on the installing host (present on MiOS and its live media).
- With the shipped bootc (1.16.x), `to-disk` partitions with sfdisk, so
  partition sizes need the `to-filesystem` leg.

### Done when
- `mios-install disk` and `existing-root` have installed MiOS on real
  hardware and the result boots and upgrades (not yet verified).
- The offline path is exercised from USB media (it sets `--target-imgref`).

## Implementation

- `tools/native/mios-install` -- `disk`, `filesystem`, `existing-root`.
- `usr/libexec/mios/deploy/baremetal_install.py` -- compatibility shim that
  forwards to `mios-install disk`.
- `tools/install.sh` -- offline USB front end: `mios-install disk --source
  oci-archive:<staged archive>`.

## References

- `usr/share/doc/mios/upstream/bootc.md` §Installing a bootc image
- `.research/native-installer-bootc-prior-art-2026-10.md`
- ADR-0005 (sovereign run-off-M), ADR-0008 (MiOS-Cat unified entry point)
- Architectural Laws 3, 4, 12, 14 (`usr/share/mios/mios.toml` `[laws]`)

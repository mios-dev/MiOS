<!-- AI-hint: Documentation of the Fedora bootc upstream lineage, detailing how MiOS integrates Anaconda kickstarts, RHEL image-mode FIPS patterns, and why MiOS builds FROM ucore-hci (not fedora-bootc directly) for the NVIDIA/virtualization plumbing its hardware-accelerated AI plane presupposes. -->
# Fedora bootc

> **Purpose.** This doc records the *upstream lineage* below MiOS: the Fedora
> bootc / Fedora CoreOS image-mode model that makes MiOS what it is — an
> immutable, OCI-shaped operating system you boot, `bootc upgrade` like a
> `git pull`, and `bootc rollback` like a Ctrl-Z. That lineage is the
> foundation the rest of MiOS stands on: because the whole OS is one
> rebuildable container image, the local agentic AI stack baked into that same
> image (inference lanes → agent-pipe/Hermes orchestration → PostgreSQL+pgvector
> memory) ships and reproduces *with* the OS, version-locked, on every host that
> pulls the ref. Audience: anyone tracing where MiOS's bootc behaviour comes
> from, or considering a different upstream base.

MiOS's lineage upstream of `ucore-hci` is **Fedora bootc / Fedora CoreOS**.
MiOS does not build `FROM` it directly (see the last section), but Fedora bootc
is where the image-mode contract — read-only composefs `/usr`, 3-way `/etc`
merge, transactional `bootc` upgrade/rollback — originates. Architectural Laws 1
(USR-OVER-ETC) and 3 (BOUND-IMAGES) exist to keep MiOS faithful to that contract
so the image stays deterministic and atomic. See
`usr/share/doc/mios/concepts/architecture.md` for how MiOS layers on top of it.

## Base images

- `quay.io/fedora/fedora-bootc` — official Fedora bootc images.
- Tags: `42`, `43`, `rawhide`. Fedora 44 was branched from rawhide in early 2026.
- Building blocks: <https://gitlab.com/fedora/bootc/base-images>

These are the canonical reference for the image-mode model; MiOS's actual base
(`ghcr.io/ublue-os/ucore-hci:stable-nvidia`, set via `[image].base` in
`usr/share/mios/mios.toml`) is a downstream of this same lineage.

## Anaconda integration

Fedora's installer (Anaconda) supports a bootc kickstart command of the form:

```
bootc --source-imgref=registry:quay.io/fedora/fedora-bootc:rawhide
```

MiOS uses BIB's `--type anaconda-iso` (which wraps Anaconda) to produce its own
installer ISO — one of the disk artifacts cut from the OCI image so MiOS can be
installed bare-metal, not just pulled with `bootc switch`. See `Justfile`'s
`iso` target and `config/artifacts/iso.toml`.

- Anaconda bootc kickstart guide: <https://fedoramagazine.org/introducing-the-new-bootc-kickstart-command-in-anaconda/>
- Building your own bootc desktop: <https://fedoramagazine.org/building-your-own-atomic-bootc-desktop/>

## RHEL "image mode" (sibling)

Red Hat ships the same model as RHEL image mode:

- RHEL 9 image mode: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/index>
- RHEL 10 FIPS in bootc: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/enabling-the-fips-mode-while-building-a-bootc-image>

MiOS's FIPS posture follows this RHEL image-mode pattern: a `kargs.d` entry plus
`update-crypto-policies --set FIPS` at build time. The kargs side lives in
`usr/lib/bootc/kargs.d/` (processed in lexicographic order); the hardening
rationale is in `usr/share/doc/mios/guides/security.md`, which also covers the
related composefs `enabled = verity` tamper-evidence the same image-mode lineage
makes possible.

## CentOS Stream bootc

`quay.io/centos-bootc/centos-bootc` is the CentOS Stream sibling. The
`bootc-image-builder` (BIB) image MiOS uses to convert its OCI image into
qcow2/raw/iso/vhdx disk artifacts is published from this lineage:
`quay.io/centos-bootc/bootc-image-builder:latest` (`Justfile:34`, mirrored as
`[image].bib` in `usr/share/mios/mios.toml`). BIB is what turns the single image
the build pipeline produces into the installable forms the bootc lifecycle then
deploys.

## Why MiOS doesn't FROM `fedora-bootc:rawhide` directly

MiOS uses `ghcr.io/ublue-os/ucore-hci:stable-nvidia` instead. `ucore-hci` is
itself Fedora CoreOS + uCore + HCI tooling, and it adds the NVIDIA proprietary
akmods (MOK-signed), libvirt/KVM/QEMU, VFIO-PCI passthrough, ZFS kernel modules,
and virtualization plumbing that the plain `fedora-bootc` base does not.

MiOS's pillars — transactional integrity, hardware acceleration, and
defense-in-depth (`usr/share/doc/mios/concepts/architecture.md`) — presuppose
those are already present. In particular, MiOS being **both** an immutable
workstation **and** a hardware-accelerated local AI OS depends on the GPU and
virtualization stack the `ucore-hci` variant ships: the same CDI/NVIDIA wiring
that lets the inference lanes (`mios-llm-light` on `:11450`, the gated heavy
GPU lanes) claim the GPU is what lets VFIO pass a discrete GPU to a VM. Starting
from bare `fedora-bootc` would mean re-building all of that downstream. Details:
`usr/share/doc/mios/upstream/ucore-hci.md`.

## Cross-refs

- `usr/share/doc/mios/upstream/ucore-hci.md` — the image MiOS actually builds `FROM`.
- `usr/share/doc/mios/upstream/bib.md` — the bootc-image-builder details.
- `usr/share/doc/mios/guides/deploy.md` — bootc Day-2 lifecycle (`upgrade`/`rollback`).
- `usr/share/doc/mios/guides/security.md` — FIPS, composefs verity, image-mode hardening.
- `usr/share/doc/mios/concepts/architecture.md` — how MiOS layers on the lineage.

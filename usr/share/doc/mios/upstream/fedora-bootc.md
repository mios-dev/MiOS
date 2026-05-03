# Fedora bootc

> MiOS's lineage upstream of ucore-hci is Fedora bootc / Fedora CoreOS.

## Base images

- `quay.io/fedora/fedora-bootc` — official Fedora bootc images
- Tags: `42`, `43`, `rawhide`. Fedora 44 was branched from rawhide in early 2026.
- Building blocks: <https://gitlab.com/fedora/bootc/base-images>

## Anaconda integration

Fedora's installer (Anaconda) supports a bootc kickstart command of the
form:

```
bootc --source-imgref=registry:quay.io/fedora/fedora-bootc:rawhide
```

'MiOS' uses BIB's `--type anaconda-iso` (which wraps Anaconda) to produce
its own installer ISO. See `Justfile:iso` and `config/artifacts/iso.toml`.

- Anaconda bootc kickstart guide: <https://fedoramagazine.org/introducing-the-new-bootc-kickstart-command-in-anaconda/>
- Building your own bootc desktop: <https://fedoramagazine.org/building-your-own-atomic-bootc-desktop/>

## RHEL "image mode" (sibling)

Red Hat ships the same model as RHEL image mode:

- RHEL 9 image mode: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/index>
- RHEL 10 FIPS in bootc: <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/enabling-the-fips-mode-while-building-a-bootc-image>

The 'MiOS' FIPS recipe (`usr/share/doc/mios/40-kargs.md` §FIPS) follows
the RHEL image-mode pattern: a kargs.d entry plus
`update-crypto-policies --set FIPS` at build time.

## CentOS Stream bootc

`quay.io/centos-bootc/centos-bootc` is the CentOS Stream sibling. The
`bootc-image-builder` image 'MiOS' uses is published from this lineage:
`quay.io/centos-bootc/bootc-image-builder:latest` (`Justfile:14`).

## Why 'MiOS' doesn't FROM `fedora-bootc:rawhide` directly

'MiOS' uses `ghcr.io/ublue-os/ucore-hci:stable-nvidia` instead — ucore-hci
adds the NVIDIA, libvirt/KVM, ZFS, and virtualization plumbing that
fedora-bootc base does not. MiOS's pillars (transactional integrity,
hardware acceleration, defense-in-depth — `ARCHITECTURE.md`) presuppose
these are already there.

## Cross-refs

- `usr/share/doc/mios/upstream/ucore-hci.md`
- `usr/share/doc/mios/upstream/bib.md`
- `usr/share/doc/mios/90-deploy.md`

<!-- AI-hint: Documentation for the bootc-image-builder (BIB) tool, detailing how MiOS uses it to transform the localhost/mios:latest OCI image into deployable disk artifacts (raw, anaconda-iso, qcow2, vhd→vhdx, wsl2) via Justfile recipes and config/artifacts/*.toml configurations. BIB is the last stage of the MiOS build pipeline before the bootc deploy/upgrade/rollback lifecycle. -->
# bootc-image-builder (BIB)

## Purpose — where BIB sits in the whole

MiOS is one OS built two ways at once: an **immutable, bootc/OCI-shaped Fedora
workstation** — the entire system is a single container image you boot,
`bootc upgrade` like a `git pull`, and `bootc rollback` like a Ctrl-Z — that is
*also* a local, self-replicating, agentic AI operating system. The MiOS build
pipeline (`Containerfile` + numbered `automation/NN-*.sh` scripts) assembles that
one image, `localhost/mios:latest`, ending in `bootc container lint`
(Architectural Law 4).

**bootc-image-builder is the bridge from that image to bootable media.** An OCI
image is the canonical artifact and the upgrade unit, but you cannot put an OCI
image directly onto bare metal, a hypervisor, or WSL — BIB converts the *same
already-built image* into installable/bootable disk artifacts (`raw`, installer
`iso`, `qcow2`, Hyper-V `vhd`→`vhdx`) under `output/`. After the artifact boots
once, the host is on the bootc lifecycle and pulls subsequent updates as OCI
images directly — so BIB matters most for **first install**, while
`bootc upgrade`/`rollback` carry the system forward. Because BIB reads the
already-built image, the image-defining Architectural Laws (deterministic,
self-contained, bound images) hold automatically in every artifact it cuts; the
local agent stack and all the OS capabilities ship inside the same image, not
bolted on per-target.

This doc is the operator/build-author reference for the BIB tool itself: which
output types MiOS produces, the recipes that produce them, the TOML schema, and
the gotchas that bit us.

> Image: `quay.io/centos-bootc/bootc-image-builder:latest`
> (`Justfile:34`, `MIOS_IMG_BIB`; overridable via `MIOS_BIB_IMAGE`).
> Used by MiOS to convert `localhost/mios:latest` (the OCI image built by
> `just build`) into deployable disk artifacts under `output/`.
> Source: `Justfile`, `usr/share/doc/mios/guides/deploy.md`,
> `config/artifacts/{bib,iso,qcow2,vhdx,wsl2}.toml`.

## Project

- Repo: <https://github.com/osbuild/bootc-image-builder>
- Docs: <https://osbuild.org/docs/bootc/>
- Successor under evaluation: <https://github.com/osbuild/image-builder-cli>
  (first-class SBOM + cross-arch; `image-versions.yml` has commented-out
  `image_builder_cli_digest` entries ready for Renovate)

## Output types

Every recipe runs `just build` first (the OCI image must exist before any BIB
leg, since BIB reads from `/var/lib/containers/storage`).

| Type | MiOS Justfile recipe | Output location | Notes |
| --- | --- | --- | --- |
| `raw` | `just raw` | `output/*.raw` | ext4 root; bootable disk image |
| `anaconda-iso` | `just iso` | `output/*.iso` | **Mount ONLY `iso.toml` — see warning below** |
| `qcow2` | `just qcow2` | `output/*.qcow2` | requires `MIOS_USER_PASSWORD_HASH` (+ optional `MIOS_SSH_PUBKEY`) |
| `vhd` | `just vhdx` (then `qemu-img convert`) | `output/*.vhdx` | BIB emits VPC `.vhd`; converted to `.vhdx` |
| `wsl2` | `just wsl2` | `output/wsl2/mios-rootfs.tar.gz` | **not a BIB type** — `podman export` of the rootfs for `wsl --import` |
| `vmdk` | (not currently in Justfile) | — | available |
| `gce` | (not currently in Justfile) | — | available |
| `ami` | (not currently in Justfile) | — | available |

> WSL2 is the one target BIB does not produce. `just wsl2` exports the image
> rootfs (`podman create` → `podman export | gzip`) for `wsl --import`, because
> BIB has no `--type wsl2`. Listed here so the full deploy-target matrix lives in
> one place.

## Critical: ISO recipe gotcha

The `iso` recipe **only mounts `iso.toml`**. Mounting both `bib.toml`
and `iso.toml` causes BIB to crash with:

```
found config.json and also config.toml
```

This is the `Justfile:iso` v0.2.0 fix. If you author a new BIB type, mount
exactly one config TOML.

## TOML schema (high-level)

The real installer config is `config/artifacts/iso.toml`. It pins the root
filesystem size, blacklists `nouveau` at install time, and — because BIB issue
#528 makes `[customizations.user]` ignored when a kickstart is present — defines
the user *inside* the kickstart:

```toml
# config/artifacts/iso.toml — abridged
[customizations.kernel]
append = "rd.driver.blacklist=nouveau modprobe.blacklist=nouveau iommu=pt"

[[customizations.filesystem]]
mountpoint = "/"
minsize    = "150 GiB"

[customizations.installer.modules]
disable = ["org.fedoraproject.Anaconda.Modules.Users"]   # user created in kickstart

[customizations.installer.kickstart]
contents = """
text --non-interactive
zerombr
clearpart --all --initlabel --disklabel=gpt
reqpart --add-boot
part / --grow --fstype ext4
network --bootproto=dhcp --device=link --activate --onboot=on
user --name=mios --groups=wheel,render,video --iscrypted --password=$6$REPLACEME_WITH_SHA512_HASH$REPLACEME
sshkey --username=mios "ssh-ed25519 AAAA_REPLACE_WITH_REAL_PUBKEY mios@operator"
reboot --eject
"""
```

Mutually exclusive sections:

- `[customizations.user]` ⊻ `[customizations.installer.kickstart]`
  (BIB #528: the kickstart wins; define the user there)
- (other top-level sections coexist freely)

## VHDX conversion idiom (`Justfile:vhdx`)

```bash
sudo podman run --rm --privileged ... ${BIB} build --type vhd --rootfs ext4 ${LOCAL}
qemu-img convert -f vpc -O vhdx output/*.vhd output/*.vhdx
rm -f output/*.vhd
```

BIB emits VPC format (`.vhd`); Hyper-V Gen 2 needs `.vhdx`.
`qemu-img` is the universal converter. The recipe no-ops the conversion (and
retains the `.vhd`) when `qemu-img` is absent.

## Password hash & SSH key substitution

`qcow2` and `vhdx` recipes `sed`-substitute env vars into a
`mktemp`-staged copy of the TOML at build time:

- `MIOS_USER_PASSWORD_HASH` (from `openssl passwd -6 'pass'`) replaces
  the placeholder `$6$REPLACEME_WITH_SHA512_HASH$REPLACEME`
- `MIOS_SSH_PUBKEY` replaces `AAAA_REPLACE_WITH_REAL_PUBKEY`

This keeps secrets out of the committed TOMLs. `just qcow2`/`just vhdx` fail fast
if `MIOS_USER_PASSWORD_HASH` is unset.

## Cross-refs

- `usr/share/doc/mios/guides/deploy.md` — operator deploy guide (the full
  artifact → install → first-boot path)
- `usr/share/doc/mios/upstream/deploy-targets.md` — per-target matrix
- `Justfile` — `raw` / `iso` / `qcow2` / `vhdx` / `wsl2` / `all` recipes

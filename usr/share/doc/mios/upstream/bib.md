# bootc-image-builder (BIB)

> Image: `quay.io/centos-bootc/bootc-image-builder:latest` (`Justfile:14`).
> Used by 'MiOS' to convert `localhost/mios:latest` (the OCI image) into
> deployable disk artifacts under `output/`. Source: `Justfile`,
> `DEPLOY.md`, `config/artifacts/{bib,iso,qcow2,vhdx,wsl2}.toml`.

## Project

- Repo: <https://github.com/osbuild/bootc-image-builder>
- Docs: <https://osbuild.org/docs/bootc/>
- Successor under evaluation: <https://github.com/osbuild/image-builder-cli>
  (first-class SBOM + cross-arch; `image-versions.yml` has commented-out
  `image_builder_cli_digest` entries ready for Renovate)

## Output types

| Type | 'MiOS' Justfile recipe | Output location | Notes |
| --- | --- | --- | --- |
| `raw` | `just raw` | `output/*.raw` | 80 GiB ext4 default |
| `anaconda-iso` | `just iso` | `output/*.iso` | **Mount ONLY `iso.toml` — see warning below** |
| `qcow2` | `just qcow2` | `output/*.qcow2` | requires `MIOS_USER_PASSWORD_HASH` |
| `vhd` | `just vhdx` (then qemu-img convert) | `output/*.vhdx` | BIB emits VPC `.vhd`; converted to `.vhdx` |
| `wsl2` | `just wsl2` | `output/*.wsl2` | tar.gz for `wsl --import` |
| `vmdk` | (not currently in Justfile) | — | available |
| `gce` | (not currently in Justfile) | — | available |
| `ami` | (not currently in Justfile) | — | available |

## Critical: ISO recipe gotcha

The `iso` recipe **only mounts `iso.toml`**. Mounting both `bib.toml`
and `iso.toml` causes BIB to crash with:

```
found config.json and also config.toml
```

This is a `Justfile:iso` v0.2.0 fix. If you author a new BIB type, mount
exactly one config TOML.

## TOML schema (high-level)

```toml
# config/artifacts/iso.toml — illustrative
[customizations.installer.kickstart]
contents = """
text --non-interactive
zerombr
clearpart --all --initlabel --disklabel=gpt
autopart --noswap --type=lvm
network --bootproto=dhcp --device=link --activate --onboot=on
"""

[customizations.installer.modules]
disable = ["org.fedoraproject.Anaconda.Modules.Users"]   # users created at first boot
```

Mutually exclusive sections:

- `[customizations.user]` ⊻ `[customizations.installer.kickstart]`
- (other top-level sections coexist freely)

## VHDX conversion idiom (`Justfile:vhdx`)

```bash
sudo podman run --rm --privileged ... ${BIB} build --type vhd --rootfs ext4 ${LOCAL}
qemu-img convert -f vpc -O vhdx output/*.vhd output/*.vhdx
rm -f output/*.vhd
```

BIB emits VPC format (`.vhd`); Hyper-V Gen 2 needs `.vhdx`.
`qemu-img` is the universal converter.

## Password hash & SSH key substitution

`qcow2` and `vhdx` recipes `sed`-substitute env vars into a
`mktemp`-staged copy of the TOML at build time:

- `MIOS_USER_PASSWORD_HASH` (from `openssl passwd -6 'pass'`) replaces
  the placeholder `$6$REPLACEME_WITH_SHA512_HASH$REPLACEME`
- `MIOS_SSH_PUBKEY` replaces `AAAA_REPLACE_WITH_REAL_PUBKEY`

This keeps secrets out of the committed TOMLs.

## Cross-refs

- `usr/share/doc/mios/90-deploy.md`
- `usr/share/doc/mios/upstream/deploy-targets.md`
- `Justfile`

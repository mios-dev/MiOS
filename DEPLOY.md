# Deployment

This document covers how to deploy a built 'MiOS' image. For build
instructions see `SELF-BUILD.md`.

## Targets

'MiOS' produces one OCI image and several disk-image artifacts derived
from it via `bootc-image-builder` (BIB) — see `Justfile`:

| Target | `just` recipe | BIB config | Output |
|---|---|---|---|
| OCI image | `just build` | — | `localhost/mios:latest` |
| RAW (80 GiB ext4) | `just raw` | `config/artifacts/bib.toml` | `output/*.raw` |
| Anaconda ISO | `just iso` | `config/artifacts/iso.toml` | `output/*.iso` |
| QCOW2 | `just qcow2` | `config/artifacts/qcow2.toml` | `output/*.qcow2` |
| VHDX (Hyper-V) | `just vhdx` | `config/artifacts/vhdx.toml` | `output/*.vhdx` |
| WSL2 tarball | `just wsl2` | `config/artifacts/wsl2.toml` | `output/*.wsl2` |

`qcow2` and `vhdx` require `MIOS_USER_PASSWORD_HASH` (`openssl passwd -6
'<pass>'`) and optionally `MIOS_SSH_PUBKEY` in the environment; the
recipes substitute these into the BIB config at build time.

## Bootc-managed Fedora host (preferred)

End-user install (from `mios-bootstrap.git`):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.sh)"
```

The bootstrap installer prompts for username, hostname, password (all
defaulting to `mios`), then runs:

```bash
sudo bootc switch ghcr.io/mios-dev/mios:latest
sudo systemctl reboot
```

Day-2 lifecycle:

```bash
sudo bootc upgrade && sudo systemctl reboot   # Pull and stage next image
sudo bootc switch <ref>                       # Move to a different tag
sudo bootc rollback                           # Undo most recent upgrade
```

## FHS Fedora Server host (non-bootc)

The same one-liner. On a non-bootc host, bootstrap clones this repo and
runs the FHS overlay applier at `install.sh` to populate `/usr/lib/`,
`/etc/`, etc. directly.

`install.sh` refuses to run on a bootc-managed host — switch via
`bootc switch` instead.

## ISO install

Boot the Anaconda ISO produced by `just iso`, run the installer, reboot.
On first boot the deployed system runs `bootc upgrade` to align with the
remote tag.

## VM install

Hyper-V: import `output/*.vhdx`, attach Gen 2 VM, enable Secure Boot
with the Microsoft UEFI CA.

QEMU/KVM: `qemu-system-x86_64 -enable-kvm -drive file=output/*.qcow2,if=virtio
-bios /usr/share/edk2/ovmf/OVMF_CODE.fd ...`.

WSL2: `wsl --import 'MiOS' C:\WSL\'MiOS' output/disk.wsl2`.

## Image verification

CI signs every tag with cosign keyless (`.github/workflows/mios-ci.yml`).
Verify before deploy:

```bash
cosign verify \
  --certificate-identity-regexp="https://github.com/mios-dev/mios" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/mios-dev/mios:latest
```

## Configuration surfaces

| Surface | Path | Editable |
|---|---|---|
| Identity (user, hostname) | `/etc/mios/install.env` | First-boot bootstrap, then admin |
| Service-level config | `/etc/mios/manifest.json` | Admin |
| Quadlet sidecars | `/etc/containers/systemd/mios-*.container` | Admin via drop-ins |
| Kernel kargs | `/usr/lib/bootc/kargs.d/*.toml` (vendor) or `bootc kargs edit` (admin) | Admin |
| Sysctl | `/etc/sysctl.d/` overrides `/usr/lib/sysctl.d/99-mios-*.conf` | Admin |
| AI prompt | `/etc/mios/ai/system-prompt.md` overrides `/usr/share/mios/ai/system.md` | Admin |

## Verification on a deployed host

```bash
bootc status                              # Image ref, deployment state
systemctl --failed                        # Any failed units
mios "what is the current image tag?"     # Local AI sanity
firewall-cmd --list-all                   # Firewall posture
getenforce                                # SELinux mode (must be Enforcing)
```

## References

- `Justfile` (`just --list` for the full target set)
- bootc: <https://bootc-dev.github.io/bootc/>
- bootc-image-builder: <https://github.com/osbuild/bootc-image-builder>
- Bootstrap repo (user-facing install): <https://github.com/mios-dev/mios-bootstrap>

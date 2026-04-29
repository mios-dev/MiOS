<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# MiOS upstream adoption playbook

**Bottom line up front.** The single highest-leverage move you can make in the next sprint is to stop hand-rolling plumbing and instead **layer `ghcr.io/ublue-os/akmods-nvidia-open` + `ghcr.io/ublue-os/akmods` into your Containerfile, adopt `uupd` as your updater, enable `composefs.enabled = verity` in `/usr/lib/ostree/prepare-root.conf`, and switch to cosign keyless signing with a GitHub Actions attest-build-provenance step.** Those four changes alone give you signed Secure-Boot-compatible NVIDIA kmods, a working update service with desktop notifications, tamper-evident roots, and verifiable supply chain — all with code already proven in Bluefin/Bazzite/ucore at production scale. Everything else in this report is additive. The second-order priority is Podman-machine-backend compliance (sshd on :22, a `core`/`user` passwordless-sudo account, CDI refresh via `nvidia-cdi-refresh.path`, and a WSL systemd shim), which unlocks `podman machine init --image ghcr.io/mios-project/mios:latest` as your Windows dev loop. The third-order work — Gamescope session, Looking Glass kvmfr, K3s/Ceph/HA — is genuinely pioneering; you will be writing patterns upstream doesn't have, and the report flags exactly where that boundary lies so you can plan accordingly.

This report has two scope notes. (1) The repo `github.com/mios-project/mios` was inaccessible during research (returned permissions errors and no search hits), so gap analysis is framed against the *typical* custom-bootc repo; substitute your actual Containerfile paths when applying recommendations. (2) `bootc` canonically lives at `github.com/bootc-dev/bootc` as of late 2025; older references to `containers/bootc` redirect.

## Executive summary: top 10 highest-value upstream adoptions, ranked

The ranking below weights *impact × confidence × implementation cost*. Items 1–4 are mandatory for a credible 1.0 release; items 5–7 unlock new deployment targets; items 8–10 are defense-in-depth worth sequencing after the first ship.

| Rank | Adoption | Source to mine | Why it wins |
|---|---|---|---|
| 1 | **COPY signed akmod RPMs from ublue-os/akmods + akmods-nvidia-open** | `ghcr.io/ublue-os/akmods*`, `build_files/base/03-install-kernel-akmods.sh` | RTX 4090 Secure-Boot-signed out of the box; avoids maintaining your own MOK infra |
| 2 | **`uupd` as the updater service** | `github.com/ublue-os/uupd` + `ublue-os/packages` | Single Go binary supersedes `bootc-fetch-apply-updates.timer` + flatpak timer + distrobox timer; Polkit rules + libnotify UX |
| 3 | **`composefs.enabled = verity` in `prepare-root.conf`** | `github.com/bootc-dev/bootc` filesystem docs; `ublue-os/main#608` | Tamper-evident root; fsverity-backed; already default-on for fedora-bootc base but you should promote to `verity` mode |
| 4 | **cosign keyless + `actions/attest-build-provenance` + `policy.json`** | `secureblue/secureblue` workflows; `ublue-os/main` cosign.pub pattern | Verifiable GHCR pulls; SLSA L3 provenance; zero secret management |
| 5 | **Greenboot-rs health checks + `bootc rollback` wiring** | Fedora 43 Change: greenboot-rs; `docs.redhat.com` RHEL image mode | Automatic boot-failure rollback; one drop-in script in `/etc/greenboot/check/required.d/` |
| 6 | **Podman-machine backend compatibility shim** | `containers/podman-machine-os` + `containers/podman-machine-wsl-os` (now merged) | `podman machine init --image ghcr.io/mios-project/mios:latest` becomes your Windows dev loop |
| 7 | **`nvidia-cdi-refresh.path` + `.service`** | `nvidia-container-toolkit` ≥ 1.18 | First-boot CDI generation done correctly — no brittle build-time spec |
| 8 | **`/usr/lib/bootc/kargs.d/*.toml`** for NVIDIA + VFIO + IOMMU | bootc docs; `ublue-os/bluefin` `03-install-kernel-akmods.sh` L92-94 | Kargs that survive upgrades without grubby hacks |
| 9 | **SecureBlue sysctl/systemd hardening drop-ins (selective)** | `secureblue/secureblue` `files/` tree | Free hardening wins that don't break NVIDIA or libvirt |
| 10 | **BlueBuild recipe.yml for multi-variant** (MiOS-1, MiOS-2) | `github.com/blue-build` | Matrix builds from one repo with modular recipe stages |

Everything else — Gamescope, Waydroid, Looking Glass, K3s, Ceph, Pacemaker — is real work but lower priority; adopt after the foundation is solid.

## Podman machine-os integration guide

### What Podman actually requires of a machine image

Podman's `pkg/machine` expects a VM/distro that exposes an **sshd on port 22** (WSL uses 2222 forwarded), a **passwordless-sudo default user** (`core` on FCOS, `user` on Fedora WSL machine-os), an **SSH public key pre-injected via Ignition or cloud-init or systemd-credentials**, and a **reachable Podman API socket at `/run/podman/podman.sock`** (rootful) or `/run/user/1000/podman/podman.sock` (rootless). The host-side binary on Windows/macOS speaks SSH → port-forwards / named-pipe-proxies the socket.

Upstream-published tags live at `quay.io/podman/machine-os:<podman-version>` (Hyper-V/QEMU/AppleHV) and `quay.io/podman/machine-os-wsl:<podman-version>` (WSL). The WSL image is a **zstd-compressed rootfs tarball** built from `docker.io/library/fedora` (not CoreOS; confirmed in `containers/podman-machine-wsl-os`) with `podman` + toolkit added on top. Builds run every 3 hours via Cirrus CI; when either the base Fedora image or the Podman package changes, a new release is tagged and pushed. Since **v5.6, WSL image builds merged into `containers/podman-machine-os`** (the old `podman-machine-wsl-os` is deprecated but still illustrative).

### Apply flow and `bootc switch`

`podman machine os apply <image> <machine>` runs `bootc switch` inside the guest. Supported transports: `docker://`, `oci-archive:`, `containers-storage:`. That means **any bootc image (including MiOS) can be applied today with `podman machine os apply ghcr.io/mios-project/mios:latest podman-machine-default`** as long as the image satisfies the machine contract below. Note WSL-based machines are documented as *not* upgradable via `os apply` — users fall back to `podman machine ssh` + dnf; however since WSL machine-os is now a bootc image, `bootc switch` should work, just unsupported officially.

### Minimal Containerfile stanza for Podman-machine compatibility

```dockerfile
# MiOS Podman-machine compatibility layer
RUN dnf -y install \
      openssh-server openssh-clients sudo polkit \
      podman podman-plugins podman-docker containers-common \
      qemu-guest-agent cloud-init wget \
      nvidia-container-toolkit-base nvidia-container-toolkit \
 && systemctl enable sshd podman.socket qemu-guest-agent cloud-init.service \
 && useradd -m -G wheel -s /bin/bash core \
 && echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/wheel-nopasswd \
 && install -Dm0644 /dev/stdin /etc/ssh/sshd_config.d/10-machine.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
AcceptEnv LANG LC_*
EOF
```

### First-boot CDI generation (the right way)

Ship this as `/usr/lib/systemd/system-preset/91-mios-nvidia.preset`:

```
enable nvidia-cdi-refresh.path
enable nvidia-cdi-refresh.service
enable nvidia-persistenced.service
```

The `nvidia-cdi-refresh.path` unit ships in `nvidia-container-toolkit` ≥ 1.18 and watches `/dev/nvidia*` / `/dev/dxg`. When the device appears on first boot, it triggers `nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml`. Override target via `/etc/nvidia-container-toolkit/cdi-refresh.env` if you want `/etc/cdi`. **Do not generate CDI at build time** — no GPU in the build sandbox, and the spec is host-specific.

### WSL detection and CDI strategy

Ship `/usr/lib/systemd/system/mios-cdi-detect.service`:

```ini
[Unit]
Description=MiOS CDI spec detection and selection
Before=nvidia-cdi-refresh.service
ConditionPathExists=!/var/lib/mios/cdi-selected

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/libexec/mios/select-cdi-spec
[Install]
WantedBy=multi-user.target
```

`/usr/libexec/mios/select-cdi-spec` is a tiny shell script that branches on `/dev/dxg` presence: if present, it invokes `nvidia-ctk cdi generate --mode=wsl --output=/var/run/cdi/nvidia.yaml`; otherwise the default `--mode=auto`. This mirrors what `podman-machine-os` does implicitly via toolkit's own detection, but an explicit unit makes debugging tractable.

### WSL-specific scaffolding

Ship `/etc/wsl.conf`:

```ini
[boot]
systemd=true
command="/usr/libexec/mios-wsl-firstboot"

[user]
default=core

[interop]
enabled=true
appendWindowsPath=false

[automount]
enabled=true
options="metadata,umask=22,fmask=11"
```

Ship `/usr/libexec/mios-wsl-firstboot` that: generates host keys if missing, creates `/run/podman` symlinks, writes the SSH pubkey from `/mnt/c/ProgramData/containers/podman/id_rsa.pub` (Podman-Desktop injects here), and starts `podman.socket`. The WSL <-> Windows socket bridge is handled by Podman on the Windows side via named-pipe proxy `\\.\pipe\podman-podman-machine-default` reading from `/run/user/1000/podman/podman.sock` over WSL interop; you don't implement this, you just ensure the socket is listening and sshd accepts key auth.

### GitHub Actions pipeline parity

Mirror upstream's cadence: Cirrus CI / GitHub Actions re-runs every 3h, compares digests of `docker.io/library/fedora` (or `quay.io/fedora/fedora-bootc:rawhide`) + published Podman package, rebuilds only on change, signs with cosign keyless, pushes a `zstd`-compressed rootfs tarball for WSL alongside the OCI image for Hyper-V/QEMU.

## Per-project mining report

### ublue-os/main — base overlay

**Steal these patterns:**
- `cosign.pub` at repo root → consumers pin via `/etc/containers/policy.json`.
- `build_files/` script layout: `00-base.sh`, `01-packages.sh`, `02-services.sh`, `03-install-kernel-akmods.sh`. Highly regular and easy to mirror.
- `shared/` tree maps 1:1 to `/`. Drop in systemd presets under `shared/usr/lib/systemd/system-preset/`.
- `justfile` + `ujust` recipes under `/usr/share/ublue-os/just/` — modular, user-facing admin UX.

### ublue-os/bluefin — dev desktop patterns

- `build_files/base/03-install-kernel-akmods.sh` lines 66-95 is the canonical way to `COPY --from=ghcr.io/ublue-os/akmods-nvidia-open:${KERNEL_FLAVOR}-${FEDORA}` and install kmods in one layer.
- `03-install-kernel-akmods.sh` L92-94 sets NVIDIA kargs via `/usr/lib/bootc/kargs.d/*.toml`.
- `brew-update.service` + `brew-update.timer`: OnBootSec=10min, OnUnitInactiveSec=6h. Steal the timer schedule if you ship Homebrew.
- DX variant split: a second Containerfile stage layers `docker-ce`, `lxd`, `libvirt`, `incus` on top of base. Direct template for your MiOS-1/MiOS-2 split.
- `rpm-ostreed.conf` override: `LockLayering=true` (prevent accidental `rpm-ostree install`), `AutomaticUpdatePolicy=none` once `uupd.timer` is active.

### ublue-os/bazzite — gaming patterns (desktop-only subset)

- `spec_files/gamescope/gamescope.spec`: custom-patched Gamescope with `CAP_SYS_NICE`. Bazzite-org fork is the production-quality source.
- `desktop/shared/usr/share/wayland-sessions/gamescope-session-steam.desktop`: the session file that launches `gamescope-session-plus steam`.
- `desktop/shared/usr/lib/systemd/system/bazzite-libvirtd-setup.service`: pattern for first-boot libvirt enablement (ConditionPathExists, restorecon, state-file). Clone verbatim for MiOS libvirt setup.
- `desktop/shared/usr/share/ublue-os/just/82-bazzite-waydroid.just`: `ujust setup-waydroid` recipe — drives `sudo waydroid init` + SELinux context restore. Adopt the recipe layout; Waydroid itself is risky on pure-NVIDIA (see open questions).
- Ships `kmod-kvmfr` pre-signed via `ghcr.io/ublue-os/akmods-extra`. **Skip handheld bits** (`jupiter-fan-control`, `hhd`, `bazzite-autologin.service`, ROG/handheld udev overrides) for your workstation target.

### ublue-os/ucore + bsherman/ucore-hci — HCI patterns

Key clarification: there are **two "HCI" concepts**. `ublue-os/ucore:stable` itself ships a variant labeled HCI that adds libvirt + virtualization tools on top of ucore. Separately, `bsherman/ucore-hci` is a third-party fork adding **ZFS + libvirt** with the `stable-nvidia` tag. Your repo description says `ucore-hci:stable-nvidia`, which is the bsherman image.

- bsherman/ucore-hci delta vs ucore: adds `libvirt`, `libvirt-daemon-kvm`, `qemu-kvm`, `virt-install`, `edk2-ovmf`, `swtpm`, plus ZFS (`zfs`, `zfs-dracut`) via the akmods-zfs overlay. The `-nvidia` suffix additionally layers `akmods-nvidia` content. No K3s, no Ceph baked in.
- ucore uses Fedora's `DefaultTimeoutStopSec=45s`; HCI docs recommend overriding with a `/etc/systemd/system/libvirtd.service.d/override.conf` containing `TimeoutStopSec=120s` so slow VMs don't get SIGKILL'd. **Adopt this directly.**
- ucore as of 200.1.18 publishes **multi-arch manifests** (aarch64 + x86_64). Model your GitHub Actions matrix on ucore's current workflow.
- `mokutil --import /etc/pki/akmods/certs/akmods-ublue.der` with password `universalblue` is the enrollment instruction users follow. **Ship this same cert path** so users can use existing docs.

### ublue-os/akmods — NVIDIA Secure Boot signing

- `certs/` directory holds the public `akmods-ublue.der`; private key is GitHub Actions secret.
- Build scripts sign via `/usr/src/kernels/$KERNEL/automation/sign-file sha256 <priv> <pub> <module.ko>`.
- CI verifies with `sbverify` against `kernel-sign.crt` + `akmods.crt` before GHCR push.
- Image tag convention: `${KERNEL_FLAVOR}-${FEDORA}[-${NV_MAJOR}]`. Example: `main-rawhide-580` for NVIDIA driver 580 on Rawhide.
- **For MiOS**: do not run your own signing infrastructure. COPY from ublue-os/akmods* and inherit their MOK. Document MOK enrollment in your README using the same `akmods-ublue.der` path.

### secureblue/secureblue — hardening patterns (selective adoption)

- Ships **own Secure Boot key** as of 2025 — decoupled from ublue-os MOK. **Do NOT adopt their key**; stay on ublue-os MOK for akmod compatibility.
- `specs/example.butane`: Ignition config that downloads `install_secureblue.sh` with sha256 check, disables `zincati` + `rpm-ostreed-automatic`, then runs installer. Good template for your Anaconda kickstart.
- Hardening drop-ins worth adopting that don't break NVIDIA/libvirt/gaming:
  - `/etc/sysctl.d/99-secureblue.conf`: `kernel.kptr_restrict=2`, `kernel.dmesg_restrict=1`, `kernel.yama.ptrace_scope=2`, `net.ipv4.tcp_syncookies=1`, `net.ipv6.conf.all.accept_redirects=0`, `fs.protected_symlinks=1`, `fs.protected_hardlinks=1`.
  - systemd drop-ins for sshd: `ProtectHome=true`, `PrivateTmp=true`, `NoNewPrivileges=true` (they ship these but you must verify sshd's actually fine — it is).
  - USBGuard default policy with `present-device policy=allow` (so existing USB stays) and `insert-device policy=block` (new USB blocked until approved).
- **Avoid their `hardened_malloc` LD_PRELOAD** globally — breaks CUDA, NVIDIA userspace, Steam, Proton. Scope to specific services if at all.
- Their SLSA provenance verification pattern via `ujust update-system` is the template: verifies cosign sig *and* that the image was built from a commit on their `live` branch by a GitHub-hosted runner. Adopt this verbatim once you have a stable branch model.

### Fedora CoreOS (coreos/fedora-coreos-config) — Ignition patterns

- `overlay.d/` layout shows the canonical way to ship files; already the pattern Fedora bootc inherits.
- **Ignition support on bootc is advancing but not drop-in.** As of late 2025 there's active work on `bootc install --with-overlay` (issue #190) letting Ignition-rendered trees be injected as overlays. Butane issue #428 proposes a `bootc:` target. Today the realistic path is: Ignition for disk-install provisioning (via Anaconda embedded Ignition, which works) + bootc for updates.
- `afterburn` handles cloud metadata (AWS, GCE, Azure, OpenStack); include `afterburn` in your cloud image variants.
- systemd preset model: `20-ignition.preset` enables `ignition-firstboot-complete.target`. Mirror the preset-driven approach for MiOS's first-boot stack.

### Flatcar — sysext/confext + update mechanisms

- Flatcar is the most production-deployed user of **systemd-sysext**: kubelet, Docker, runc shipped as detachable `.raw` sysext images. Realistic example if you want to ship K3s as a sysext.
- Butane profile `flatcar` transpiles to Ignition.
- Nebraska/Omaha update protocol is Flatcar-specific; **don't adopt**. Stay on bootc for MiOS.
- **Key takeaway**: sysext on Fedora Rawhide bootc is technically feasible but under-tested. Skip for MiOS 1.0; revisit when shipping optional GPU/K3s/Ceph modules.

### CentOS bootc / RHEL image mode — enterprise patterns

- `registry.redhat.io/rhel9/bootc-image-builder:latest` has the most polished BIB experience — use as reference even if you build with the CentOS variant.
- FIPS mode: set `fips=1` in `/usr/lib/bootc/kargs.d/15-fips.toml`, ship `/etc/system-fips` marker file, include `crypto-policies` package, run `fips-mode-setup --enable` at build time. **Warning**: FIPS mode breaks proprietary NVIDIA drivers because NVIDIA userspace uses non-FIPS OpenSSL. **Do not ship FIPS as default on a NVIDIA workstation image.** Offer as an optional variant (MiOS-fips) only if required.
- Kickstart `ostreecontainer` directive is how Anaconda installs bootc images. Use for your installable ISO variant.

### systemd-sysext / confext / homed / sysupdate verdicts for MiOS

- **sysext**: promising but defer. Ship MiOS 1.0 as monolithic bootc image; consider extracting Gamescope + K3s as sysexts post-1.0 once Flatcar patterns are more broadly tested on Fedora bootc.
- **confext**: same as sysext — defer.
- **homed**: not ready for a multi-user workstation with NVIDIA + gaming. GDM has homed-compatible PAM but NVIDIA userspace + Steam + Waydroid haven't been fully validated. Skip.
- **sysupdate**: complements but does not compete with bootc. Some discussion in bootc issues about using sysupdate for the ESP + bootloader (bootupd is today's answer). **Skip for MiOS 1.0.**

## Composefs and fs-verity adoption roadmap

Fedora bootc base images **already enable composefs by default** in "unsigned" mode (fsverity on when the target filesystem supports it, no signature enforcement). The adoption arc for MiOS is three phases.

**Phase 1 (immediate)**: Confirm your base includes `/usr/lib/ostree/prepare-root.conf` with `[composefs] enabled = yes`. Verify on a running deployment with `cat /proc/mounts | grep composefs` — should see the overlay. No action needed beyond inheriting from `quay.io/fedora/fedora-bootc:rawhide`.

**Phase 2 (1-2 releases out)**: Promote to `composefs.enabled = verity` mode. Add this drop-in:

```toml
# /usr/lib/ostree/prepare-root.conf (override or drop-in)
[composefs]
enabled = verity
```

This hard-requires fsverity at install time — BIB will refuse to install if the target filesystem doesn't support it (ext4 and btrfs do; xfs does not as of 2025-2026 — **use ext4 or btrfs for MiOS, NOT xfs**). **Caveat**: `/etc` and `/var` mounts are unaffected; since `/etc/systemd/system/*.service` is executable config, an attacker with `/etc` write can still run code. Mitigate with `etc.transient = yes` if your threat model requires it — but this breaks many workstation workflows (persistent user SSH configs, NetworkManager keyfiles, etc.). Recommend: **do not** enable transient /etc for a workstation image; accept the /etc trust assumption.

**Phase 3 (requires upstream work)**: Full boot-chain integrity — signed composefs metadata + Unified Kernel Images (UKI). Tracked in `gitlab.com/fedora/bootc/tracker/-/issues/14`. Not ready for MiOS 1.0; watch for bootupd + UKI support to land.

**Known gotchas**:
- `systemd-remount-fs.service` fails on F42 disk images with composefs enabled (`fedora-iot/iot-distro#81`). Workaround: mask the service in your image — `ln -sf /dev/null /etc/systemd/system/systemd-remount-fs.service`.
- `chattr -i` no longer works on composefs root; derived-container modifications must happen in Containerfile, not via host `chattr`.
- kdump had bugs with composefs; track `bugzilla.redhat.com/show_bug.cgi?id=2284097`. Test kdump on your image before shipping; if broken, disable `kdump.service`.

## Signing and supply chain hardening roadmap

### Minimum viable signing workflow (ship this week)

```yaml
# .github/workflows/build-sign.yml
name: Build, sign, attest, push
on: { push: { branches: [main] }, schedule: [ { cron: '0 */6 * * *' } ] }
permissions: { contents: read, packages: write, id-token: write, attestations: write }
jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: redhat-actions/buildah-build@v2
        id: build
        with:
          image: mios
          tags: latest ${{ github.sha }}
          containerfiles: ./Containerfile
          build-args: |
            FEDORA_VERSION=rawhide
            KERNEL_FLAVOR=main
      - uses: redhat-actions/push-to-registry@v2
        id: push
        with:
          image: mios
          tags: latest ${{ github.sha }}
          registry: ghcr.io/kabuki94
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: sigstore/cosign-installer@v3
      - run: cosign sign --yes ghcr.io/mios-project/mios@${{ steps.push.outputs.digest }}
      - uses: actions/attest-build-provenance@v2
        with:
          subject-name: ghcr.io/mios-project/mios
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true
```

### Consumer policy.json for MiOS users

```json
{
  "default": [{ "type": "reject" }],
  "transports": {
    "docker": {
      "ghcr.io/mios-project/mios": [{
        "type": "sigstoreSigned",
        "keyPath": "/etc/pki/containers/mios-cosign.pub",
        "signedIdentity": { "type": "matchRepository" }
      }],
      "ghcr.io/ublue-os": [{
        "type": "sigstoreSigned",
        "keyPath": "/etc/pki/containers/ublue-cosign.pub"
      }],
      "quay.io/fedora": [{ "type": "insecureAcceptAnything" }]
    }
  }
}
```

Pair with `/etc/containers/registries.d/ghcr.io.yaml`:
```yaml
docker:
  ghcr.io:
    use-sigstore-attachments: true
```

Ship both files in the image. Users then invoke `bootc switch --enforce-container-sigpolicy ghcr.io/mios-project/mios:latest` and pulls are verified. For SLSA, extend the `ujust update-system` recipe to also run `gh attestation verify <ghcr-image> --repo mios-project/mios` before the switch.

### Generate your cosign keyless identity reference

Record in README that the expected signer identity is `https://github.com/mios-project/mios/.github/workflows/build-sign.yml@refs/heads/main` with issuer `https://token.actions.githubusercontent.com`. Users verify offline via `cosign verify --certificate-identity <...> --certificate-oidc-issuer <...> ghcr.io/mios-project/mios:latest`.

## Switch, rollback, health-check integration plan

### bootc command semantics (current reality as of bootc 1.2.x)

`bootc upgrade` pulls the registry manifest, stages a new deployment as `pending`, and applies on next shutdown/reboot via `ostree-finalize-staged.service`. Flags: `--check` (manifest-only), `--download-only` (stage but don't promote), `--apply` (reboot immediately). Soft-reboot support via systemd's soft-reboot is tracked in issue #1350, not default yet.

`bootc rollback` reorders bootloader entries: current becomes rollback, rollback becomes default. Does not create a new deployment; discards staged updates; `/etc` reverts to the rolled-back deployment's state. **Gotcha**: `bootc-fetch-apply-updates.timer` runs within 1-3 hours of rollback and re-upgrades. Plan: teach users `systemctl disable --now bootc-fetch-apply-updates.timer` before a rollback they want to persist, or pin a specific digest with `bootc switch ghcr.io/mios-project/mios@sha256:<digest>`.

`bootc switch --enforce-container-sigpolicy` forces signature verification on the target image. Always use this flag in your docs and `ujust` recipes.

### Recommended updater stack for MiOS

Don't run `bootc-fetch-apply-updates.timer` and `uupd.timer` simultaneously — they duplicate work. Pick **uupd** (Bluefin's pattern):

```dockerfile
RUN dnf5 -y copr enable ublue-os/packages \
 && dnf5 -y install uupd \
 && systemctl disable bootc-fetch-apply-updates.timer \
 && systemctl disable rpm-ostreed-automatic.timer \
 && systemctl enable uupd.timer
```

`uupd.timer` fires `OnBootSec=20min` and `OnUnitInactiveSec=6h` (Bluefin's current values). The Go binary runs bootc + flatpak + distrobox + brew updates in parallel with Polkit authorization. `/etc/uupd/config.json` exposes hardware gates (battery ≥ 20%, CPU < 50%, memory < 90%, network < 700 KB/s) so updates don't kick off mid-game.

### Greenboot-rs health checks

Greenboot-rs (Fedora 43 Change, Rust rewrite of greenboot) integrates natively with bootc. Drop your checks in `/etc/greenboot/check/required.d/` (fail → rollback) and `/etc/greenboot/check/wanted.d/` (fail → warn). Example for MiOS:

```bash
#!/usr/bin/bash
# /etc/greenboot/check/required.d/10-nvidia-cdi.sh
set -euo pipefail
test -s /var/run/cdi/nvidia.yaml || { echo "CDI missing"; exit 1; }
nvidia-smi -q >/dev/null 2>&1 || { echo "nvidia-smi failed"; exit 1; }
```

```bash
#!/usr/bin/bash
# /etc/greenboot/check/required.d/20-podman.sh
set -euo pipefail
systemctl is-active podman.socket >/dev/null || exit 1
```

```bash
#!/usr/bin/bash
# /etc/greenboot/check/wanted.d/30-libvirt.sh
set -euo pipefail
systemctl is-active libvirtd.socket >/dev/null || exit 1
```

`/etc/greenboot/greenboot.conf`: `GREENBOOT_MAX_BOOT_ATTEMPTS=3`. On 3 failed boots, grub `boot_counter` triggers `greenboot-rpm-ostree-grub2-check-fallback.service` which rolls back.

## bootc-image-builder advanced usage

### Per-target BIB invocations for MiOS

Build configs live in `./bib-configs/` in your repo, one per target. Shared fragment (`bib-configs/_shared.toml`):

```toml
[[customizations.user]]
name = "kabu"
password = "$6$..."  # yescrypt hash
key = "ssh-ed25519 AAAA..."
groups = ["wheel", "libvirt", "kvm", "docker", "video", "render"]

[[customizations.filesystem]]
mountpoint = "/"
minsize = "40 GiB"
[[customizations.filesystem]]
mountpoint = "/var"
minsize = "80 GiB"
```

**Hyper-V VHDX** (`bib-configs/hyperv.toml`): include shared + type-specific.
```
podman run --rm --privileged --pull=newer \
  -v ./bib-configs/hyperv.toml:/config.toml:ro \
  -v ./output:/output \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  quay.io/centos-bootc/bootc-image-builder:latest \
  --type vhd --rootfs ext4 --config /config.toml \
  ghcr.io/mios-project/mios:latest
```

**WSL2 tarball** (not natively a BIB output — build manually):
```bash
# Export the running image as a tar for WSL import
podman create --name tmp-wsl ghcr.io/mios-project/mios:latest /bin/true
podman export tmp-wsl | zstd -T0 -o output/mios-wsl.tar.zst
```
Users import via `wsl --import MiOS C:\WSL\MiOS mios-wsl.tar.zst --version 2`.

**QEMU qcow2**: `--type qcow2 --rootfs btrfs`. btrfs chosen over xfs for fsverity compatibility and snapshot-friendly `/var`.

**Anaconda ISO** (`bib-configs/anaconda.toml`):
```toml
[customizations.installer.kickstart]
contents = """
text --non-interactive
lang en_US.UTF-8
keyboard us
timezone --utc America/New_York
reqpart --add-boot
part / --grow --fstype=ext4
"""
[customizations.installer.modules]
enable = ["org.fedoraproject.Anaconda.Modules.Storage"]
disable = ["org.fedoraproject.Anaconda.Modules.Users"]
[customizations.iso]
volume_id = "MIOS-1"
application_id = "MiOS"
publisher = "MiOS-DEV"
```
Then `--type anaconda-iso`.

**Cloud images** (AMI/GCE/Azure): `--type ami --target-arch amd64` + credentials via environment variables. Use `bootc-image-builder-action` in CI for push-to-S3 automation.

### Known issues and workarounds

- `xfs` with composefs+verity is broken; use `ext4` or `btrfs`.
- Large NVIDIA kernel modules + `/usr/lib/modules/<kver>/extra/` can push image size past 8 GB; BIB's default `minsize` of 10 GiB may be insufficient — bump to 40 GiB root.
- Anaconda ISO + `[customizations.user]` are mutually exclusive with `[customizations.installer.kickstart]`. Use one or the other.
- Running BIB on a rootful Podman machine with bind-mounted host container storage hits `podman#27183`; workaround is to omit the host storage mount and build the bootc image inside the BIB container.
- BIB currently must run as root (vs. coreos-assembler which needs only `/dev/kvm`). Document this.
- Multi-arch builds: bootc container arch must match BIB arch. For aarch64 MiOS variants, use an aarch64 BIB runner or build on a Graviton GitHub Actions runner.

## Specific PACKAGES.md additions

Organize into sections so you can diff against upstream easily.

**Build infrastructure**:
`bootc`, `bootc-image-builder` (tooling only), `ostree`, `rpm-ostree`, `skopeo`, `buildah`, `cosign`, `just`.

**Security / supply chain**:
`crowdsec`, `crowdsec-firewall-bouncer-nftables`, `nftables`, `firewalld`, `policycoreutils`, `policycoreutils-python-utils`, `setools-console`, `usbguard`, `audit`, `aide`, `openscap-scanner`, `scap-security-guide`, `libpwquality`.

**Machine-OS scaffolding**:
`openssh-server`, `openssh-clients`, `sudo`, `polkit`, `cloud-init`, `qemu-guest-agent`, `spice-vdagent`, `hyperv-tools`, `wslu` (when WSL), `python3-pip`.

**Container/Kubernetes runtime**:
`podman`, `podman-plugins`, `podman-docker`, `containers-common`, `toolbox`, `distrobox`, `moby-engine` (optional — pick one), `k3s` (via COPR or tarball installer), `kubectl`, `helm`.

**NVIDIA stack (via COPY from akmods-nvidia-open)**:
`nvidia-driver`, `nvidia-driver-cuda`, `nvidia-driver-libs`, `nvidia-modprobe`, `nvidia-persistenced`, `nvidia-settings`, `libnvidia-ml`, `libnvidia-fbc`, `libnvidia-cfg`, `nvidia-container-toolkit`, `nvidia-container-toolkit-base`, `nvidia-container-selinux`, `kmod-nvidia-open` (from akmods), `ublue-os-akmods-addons`, `ublue-os-nvidia-addons`.

**Virtualization / VFIO**:
`libvirt`, `libvirt-daemon-kvm`, `libvirt-dbus`, `qemu-kvm`, `qemu-device-display-virtio-gpu`, `edk2-ovmf`, `swtpm`, `swtpm-tools`, `virt-install`, `virt-viewer`, `virt-manager`, `libguestfs-tools`, `dnsmasq`, `cockpit`, `cockpit-machines`, `cockpit-storaged`, `cockpit-networkmanager`, `cockpit-podman`.

**Storage (Ceph node mode)**:
`ceph-common`, `ceph-osd`, `ceph-mon`, `ceph-mgr`, `rbd-nbd` (pulled from CentOS Storage SIG COPR; not in Fedora base).

**HA**:
`pacemaker`, `corosync`, `pcs`, `fence-agents-all`, `resource-agents`, `sbd`.

**Desktop / Wayland**:
`gnome-shell`, `gnome-session-wayland-session`, `gdm`, `gnome-control-center`, `gnome-remote-desktop`, `freerdp`, `freerdp-libs`, `pipewire`, `pipewire-pulseaudio`, `wireplumber`, `xdg-desktop-portal`, `xdg-desktop-portal-gnome`, `libei`.

**Gaming (Gamescope session, desktop-only subset)**:
`gamescope`, `gamescope-session-plus`, `gamescope-session-steam`, `steam`, `steam-devices`, `mangohud`, `gamemode`, `vkbasalt`, `latencyflex-vulkan-layer`, `sddm`. (all from `bazzite-org` COPR).

**Looking Glass**:
`kmod-kvmfr` (from `ublue-os/akmods-extra` or `hikariknight/looking-glass-kvmfr` COPR).

**Waydroid** (risky on NVIDIA — optional variant):
`waydroid`, `wlroots`, `libglibutil`, `libgbinder`, `python3-pyclip`, `lxc`, `dnsmasq`.

**CrowdSec**:
`crowdsec`, `crowdsec-firewall-bouncer-nftables` (from `packagecloud.io/crowdsec/crowdsec`).

**Updater**:
`uupd` (from `ublue-os/packages` COPR).

**ujust/just scaffolding**:
`just`, `ublue-os-just`, `ublue-os-update-services` (optional if you reuse uupd directly without ublue-os main).

## Specific systemd unit files to create

**`/usr/lib/systemd/system/mios-cdi-detect.service`** — WSL vs bare-metal CDI selection oneshot (shown above).

**`/usr/lib/systemd/system/mios-libvirtd-setup.service`** — first-boot libvirt restorecon + socket enable (mirror of Bazzite's pattern).

**`/usr/lib/systemd/system/mios-crowdsec-init.service`** — first-boot bouncer key generation (shown in research notes; generates API key via `cscli bouncers add`, writes to bouncer yaml, restarts bouncer).

**`/usr/lib/systemd/system/mios-firstboot.target`** — aggregator target that pulls in all first-boot oneshots with `ConditionFirstBoot=yes`:

```ini
[Unit]
Description=MiOS first-boot provisioning target
After=multi-user.target
Requires=mios-cdi-detect.service mios-libvirtd-setup.service
```

**`/usr/lib/systemd/system-preset/90-mios.preset`**:

```
enable sshd.service
enable podman.socket
enable uupd.timer
enable greenboot-healthcheck.service
enable nvidia-cdi-refresh.path
enable nvidia-cdi-refresh.service
enable nvidia-persistenced.service
enable cockpit.socket
enable libvirtd.socket
enable crowdsec.service
enable crowdsec-firewall-bouncer.service
enable nftables.service
enable mios-cdi-detect.service
enable mios-libvirtd-setup.service
disable bootc-fetch-apply-updates.timer
disable rpm-ostreed-automatic.timer
disable systemd-remount-fs.service
```

**`/usr/lib/systemd/system/libvirtd.service.d/override.conf`**:
```ini
[Service]
TimeoutStopSec=120s
```

## Specific Containerfile snippets

### Multi-variant structure (MiOS-1 workstation + MiOS-2 server)

```dockerfile
# syntax=docker/dockerfile:1
ARG FEDORA=rawhide
ARG KERNEL_FLAVOR=main
ARG NV=580

# ----- ctx stage: package lists, scripts -----
FROM scratch AS ctx
COPY build_files/ /build_files/
COPY  /
COPY packages/ /packages/

# ----- base stage: shared by both variants -----
FROM {{MIOS_BASE_IMAGE}} AS base
COPY --from=ctx /build_files /ctx/build_files
COPY --from=ctx /system_files /ctx/system_files
COPY --from=ctx /packages /ctx/packages

# Common: akmods-nvidia-open, uupd, security
COPY --from=ghcr.io/ublue-os/akmods-nvidia-open:${KERNEL_FLAVOR}-${FEDORA}-${NV} /rpms /tmp/akmods-nvidia
COPY --from=ghcr.io/ublue-os/akmods:${KERNEL_FLAVOR}-${FEDORA} /rpms /tmp/akmods-common
COPY --from=ghcr.io/ublue-os/akmods-extra:${KERNEL_FLAVOR}-${FEDORA} /rpms /tmp/akmods-extra

RUN --mount=type=cache,dst=/var/cache/libdnf5 \
    /ctx/build_files/00-base.sh && \
    /ctx/build_files/01-akmods.sh && \
    /ctx/build_files/02-nvidia.sh && \
    /ctx/build_files/03-security.sh && \
    /ctx/build_files/04-updater.sh && \
    /ctx/build_files/05-system-files.sh

# ----- MiOS-1: workstation (GNOME, Gamescope, Waydroid, Looking Glass) -----
FROM base AS mios-1
RUN /ctx/build_files/10-desktop-gnome.sh && \
    /ctx/build_files/11-gamescope.sh && \
    /ctx/build_files/12-looking-glass.sh && \
    /ctx/build_files/13-libvirt.sh && \
    /ctx/build_files/14-waydroid.sh && \
    /ctx/build_files/99-cleanup.sh && \
    bootc container lint

# ----- MiOS-2: HA node (K3s, Ceph, Pacemaker, no desktop) -----
FROM base AS mios-2
RUN /ctx/build_files/20-k3s.sh && \
    /ctx/build_files/21-ceph.sh && \
    /ctx/build_files/22-ha-pacemaker.sh && \
    /ctx/build_files/99-cleanup.sh && \
    bootc container lint
```

GitHub Actions matrix:
```yaml
strategy:
  matrix:
    variant: [mios-1, mios-2]
    include:
      - variant: mios-1
        dockerfile-target: mios-1
      - variant: mios-2
        dockerfile-target: mios-2
```

### NVIDIA kargs drop-in
```dockerfile
RUN install -Dm0644 /dev/stdin /usr/lib/bootc/kargs.d/10-nvidia.toml <<'EOF'
kargs = [
  "rd.driver.blacklist=nouveau",
  "modprobe.blacklist=nouveau",
  "nvidia-drm.modeset=1",
  "nvidia-drm.fbdev=1",
  "nvidia.NVreg_PreserveVideoMemoryAllocations=1",
]
EOF
```

### VFIO kargs drop-in
```dockerfile
RUN install -Dm0644 /dev/stdin /usr/lib/bootc/kargs.d/20-vfio.toml <<'EOF'
kargs = [
  "amd_iommu=on",
  "iommu=pt",
  "rd.driver.pre=vfio-pci",
  "kvm.ignore_msrs=1",
]
EOF
```

### Ensure trust policy is baked in
```dockerfile
COPY etc/pki/containers/ /etc/pki/containers/
COPY etc/containers/policy.json /etc/containers/policy.json
COPY etc/containers/registries.d/ /etc/containers/registries.d/
```

## Open questions and gaps — what MiOS will need to pioneer

These are the areas where upstream has no finished pattern; your work here will be novel and worth upstreaming back.

**bootc + K3s declarative bootstrap**: ucore ships k3s packages but no declarative bootstrap (no "install image + reboot = working single-node cluster"). You will have to write a first-boot oneshot that runs `k3s server --write-kubeconfig=/etc/rancher/k3s/k3s.yaml` with configuration from `/etc/mios/k3s-config.yaml` (machine-local state) — model after Flatcar's `kubelet.service` sysext pattern.

**bootc + Ceph with immutable root**: OSDs need writable disk devices (raw block), which is fine on immutable root since OSDs don't need writable `/usr`. But `ceph-mon` stores state in `/var/lib/ceph` which is persistent — safe. No upstream pattern exists for ceph-on-bootc; you'll need to write it. Consider deferring to Rook-on-K3s rather than native packages — Rook is just container images, pure bootc.

**Pacemaker/Corosync on bootc**: RHEL image mode + HA add-on is the only "supported" path, and even that is thin. Corosync config lives in `/etc/corosync/corosync.conf` (persistent ✓) and `authkey` in `/etc/corosync/authkey` (persistent ✓). But stonith agents, fence configs, and resource agents assume mutable `/usr/lib/ocf/resource.d/`. You may need to ship extra resource agents via sysext — genuine new pattern.

**Looking Glass client** is not packaged anywhere (including ublue). Must build from source inside a Distrobox. Document this limitation; consider packaging it yourself as an RPM in a COPR and consuming it.

**Gamescope session on NVIDIA Wayland**: Bazzite marks this as beta. RTX 4090 should be fine but HDR + VRR through Gamescope on NVIDIA is not guaranteed. Expect to file bugs upstream.

**Waydroid on pure-NVIDIA 4090** is documented as not working reliably. If your workstation has only a 4090, plan to ship Waydroid as an optional sysext, not in the base image. Long-term fix requires NVIDIA zink/Vulkan-GBM maturity.

**RDP RemoteApp / Enhanced Session for Linux**: xrdp's RAIL is abandoned for modern Windows clients. gnome-remote-desktop is the correct path but does not support RemoteApp-style single-window streaming. If you need that, Apache Guacamole (HTML5) or Sunshine/Moonlight is the answer, not xrdp.

**Podman-machine WSL bootc upgrades** are officially unsupported (`podman machine os apply` explicitly excludes WSL). In practice `bootc switch` from inside the WSL distro works; document as "experimental, may desync with Windows-side Podman version."

**UKI + measured boot + signed composefs** full chain: tracked at `gitlab.com/fedora/bootc/tracker/-/issues/14`. Watch and wait.

**CrowdSec on Fedora Rawhide** depends on F40 RPMs from packagecloud; F41+ works, Rawhide sometimes breaks. Build-from-source fallback is unavoidable until CrowdSec publishes rawhide builds.

## Reference links

- bootc canonical repo: `github.com/bootc-dev/bootc`
- bootc docs: `bootc-dev.github.io/bootc/`
- bootc-image-builder: `github.com/osautomation/bootc-image-builder` and `osbuild.org/specs/bootc/`
- bootc-image-builder-action: `github.com/osautomation/bootc-image-builder-action`
- Fedora bootc docs (local preview, authoritative): `fedora.gitlab.io/bootc/specs/bootc/`
- Fedora bootc examples: `gitlab.com/fedora/bootc/examples`
- composefs: `github.com/containers/composefs`
- Fedora Change Composefs Atomic Desktops: `fedoraproject.org/wiki/Changes/ComposefsAtomicDesktops`
- Universal Blue main: `github.com/ublue-os/main`
- Bluefin: `github.com/ublue-os/bluefin` (especially `build_files/base/03-install-kernel-akmods.sh`)
- Bazzite: `github.com/ublue-os/bazzite` (`desktop/shared/usr/lib/systemd/system/bazzite-libvirtd-setup.service`, `desktop/shared/usr/share/ublue-os/just/82-bazzite-waydroid.just`)
- Bazzite Gamescope session fork: `github.com/bazzite-org/gamescope-session`, `github.com/bazzite-org/gamescope`
- ucore: `github.com/ublue-os/ucore`
- ucore-hci (bsherman): `github.com/bsherman/ucore-hci`
- akmods: `github.com/ublue-os/akmods`
- uupd: `github.com/ublue-os/uupd`
- BlueBuild: `github.com/blue-build`
- secureblue: `github.com/secureblue/secureblue`
- Podman machine-os: `github.com/containers/podman-machine-os`
- Podman machine-wsl-os (deprecated, merged into machine-os v5.6+): `github.com/containers/podman-machine-wsl-os`
- Podman WSL Fedora rootfs: `github.com/containers/podman-wsl-fedora`
- podman-bootc (maintenance, succeeded by bcvk): `github.com/bootc-dev/podman-bootc`
- Podman Desktop bootc extension: `github.com/podman-desktop/extension-bootc`
- NVIDIA CDI: `docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html`
- Looking Glass kvmfr akmod: `github.com/HikariKnight/looking-glass-kvmfr-akmod`; COPR: `copr.fedorainfracloud.org/coprs/hikariknight/looking-glass-kvmfr/`
- gnome-remote-desktop: `github.com/GNOME/gnome-remote-desktop`; Red Hat GRD headless docs: `docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/administering_rhel_by_using_the_gnome_desktop_environment/remotely-accessing-the-desktop`
- Waydroid: `github.com/waydroid/waydroid`
- CrowdSec install: `docs.crowdsec.net/u/getting_started/installation/linux/`; bouncer: `github.com/crowdsecurity/cs-firewall-bouncer`
- RHEL image mode docs: `docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/`
- CoreOS Ignition: `github.com/coreos/ignition`; Butane: `github.com/coreos/butane`
- Fedora Magazine bootc desktop walkthrough: `fedoramagazine.org/building-your-own-atomic-bootc-desktop/`
- supakeen on interactive bootc installers: `supakeen.com/weblog/building-interactive-installer-bootc/`
- Bluefin discussion on uupd update schedule: `github.com/ublue-os/bluefin/discussions/3715`

## Conclusion: the sequencing plan in one paragraph

Land signed akmod-nvidia-open + uupd + cosign keyless + composefs-verity in the next release — that's the credibility foundation and it's one weekend of work because every piece is `COPY --from=ghcr.io/ublue-os/...` or a one-liner drop-in. The next release after that adds Podman-machine backend compatibility (the 20-line Containerfile stanza above plus mios-cdi-detect.service) which gives you a Windows dev loop through `podman machine init --image`. Release three is greenboot-rs health checks + BIB-per-target in CI so users can grab a qcow2, VHDX, WSL tarball, or Anaconda ISO from GitHub Releases. Only then tackle the hard novel work: declarative K3s bootstrap, Ceph-on-bootc with Rook, Pacemaker HA resource agents, Gamescope-on-NVIDIA-Wayland polish. The multi-variant split (MiOS-1 desktop / MiOS-2 HA node) should be structural from day one — not a later refactor — because the `ctx` stage + matrix build is fundamentally cheaper than forking repos later. Everything about this plan is that you are borrowing 90% of your code from ublue/bazzite/ucore/secureblue and only writing the 10% that is genuinely MiOS's — which is the correct ratio for a sole-developer project that aims to ship.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

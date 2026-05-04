# 'MiOS' Engineering Reference

A reference covering every architectural decision, build pipeline phase,
supply-chain artifact, and operational law of the 'MiOS' Linux
distribution. Every claim cites a real file path.

---

## §0. Project identity

- Org: **`mios-dev`** (https://github.com/mios-dev). All earlier names --
  *CloudWS-bootc*, *CloudWS-OS* -- are deprecated.
- Two repos:
  - **System layer:** `https://github.com/mios-dev/MiOS.git` -- the bootc
    image source. Repo root *is* the deployed system root.
  - **Bootstrap/installer:** `https://github.com/mios-dev/mios-bootstrap.git` --
    Phase 0/1/4 of the global install pipeline (preflight, total root merge,
    reboot prompt).
- Published image: **`ghcr.io/mios-dev/mios:latest`**.
- Base image: **`ghcr.io/ublue-os/ucore-hci:stable-nvidia`** (overridable via
  `MIOS_BASE_IMAGE`).
- Image lifecycle: bootc-managed (`bootc switch` / `bootc upgrade` /
  `bootc rollback`).
- Target hosts: AI workstations, hyperconverged-infra single-nodes, KVM
  passthrough rigs. Not a general-purpose desktop.

---

## §1. Repository topology

### `'MiOS'` repo (system layer) -- repo root is system root

```
.                                  # = / on a deployed host
├── automation/                    # Phase-2 build pipeline (~48 NN-prefix scripts)
│   ├── build.sh                   # Master orchestrator (called by Containerfile)
│   ├── lib/
│   │   ├── common.sh              # log/warn/die helpers, dnf flags, version manifest
│   │   ├── packages.sh            # PACKAGES.md fenced-block parser
│   │   ├── masking.sh             # log secret-mask filter
│   │   └── paths.sh               # build-time MIOS_*_DIR constants
│   ├── 01-repos.sh ... 99-postcheck.sh   # Phase scripts (numeric-ordered)
│   ├── ai-bootstrap.sh            # AI manifest / Wiki / KB regeneration
│   ├── bcvk-wrapper.sh            # bootc-image-builder convenience wrapper
│   ├── bootstrap.sh               # Local-dev bootstrap helper
│   ├── enroll-mok.sh              # MOK key enrollment
│   ├── generate-mok-key.sh        # One-shot MOK key generator
│   ├── install.sh                 # System-side installer (FHS overlay path)
│   ├── install-bootstrap.sh       # Interactive ignition installer
│   └── manifest.json              # Auto-generated phase-script index
├── usr/                           # → /usr (read-only composefs)
│   ├── lib/
│   │   ├── bootc/
│   │   │   ├── kargs.d/           # Kernel arg fragments (TOML, flat array form)
│   │   │   └── bound-images.d/    # Quadlet image binders (LAW 3)
│   │   ├── mios/                  # 'MiOS' runtime libs (paths.sh, logs/)
│   │   ├── modprobe.d/            # Kernel module overrides
│   │   ├── modules-load.d/        # Module auto-load list (mios.conf)
│   │   ├── profile.d/             # MOTD + WSLg env exports
│   │   ├── sysctl.d/              # Kernel runtime tunables (90-* le9uo, 99-* hardening)
│   │   ├── sysusers.d/            # Static user/group defs (10-mios.conf is canonical)
│   │   ├── systemd/system/        # MiOS-owned units + drop-ins for stock units
│   │   ├── systemd/system-preset/ # 90-mios.preset (enable/disable defaults)
│   │   ├── tmpfiles.d/            # /var/* and /run/* tmpfiles entries (LAW 2)
│   │   └── udev/rules.d/          # Custom udev rules (99-mios-gpu, 99-kvmfr)
│   ├── libexec/
│   │   ├── mios/                  # Private exec dir (motd, role-apply, gpu-detect, etc.)
│   │   ├── mios-grd-setup         # GNOME Remote Desktop firstboot setup
│   │   └── mios-flatpak-install   # Flatpak first-boot installer
│   ├── share/
│   │   ├── containers/systemd/    # System-level Quadlet definitions
│   │   ├── doc/mios/              # Subsystem deep-dive docs (00-overview, upstream/)
│   │   ├── mios/
│   │   │   ├── PACKAGES.md        # SSOT for every RPM in the image
│   │   │   ├── env.defaults       # Vendor environment defaults
│   │   │   ├── mios.toml.example  # Vendor template for ~/.config/mios/mios.toml
│   │   │   ├── kb/manifest.json   # KB delivery index (FHS-compliant location)
│   │   │   └── ai/                # AI surface (system.md, v1/, etc.)
│   │   └── selinux/packages/mios/ # Custom SELinux .te modules
│   └── lib/extensions/source/     # systemd-sysext source materials
├── etc/                           # → /etc (3-way merge on bootc upgrade)
│   ├── containers/systemd/        # Host-level Quadlet definitions (mios-ai/ceph/k3s)
│   ├── mios/
│   │   ├── eval-criteria.json     # OpenAI Evals grader rubric
│   │   ├── kb.conf.toml           # KB-wide config
│   │   ├── system-prompts/        # Engineer/Reviewer/Troubleshoot prompts
│   │   └── ai/                    # Host-local AI overrides
│   ├── profile.d/                 # mios-motd.sh + mios-wsl2.sh login hooks
│   ├── pki/mios/                  # MOK DER cert (public key)
│   └── wsl.conf                   # WSL2 config (byte-identical to /usr/lib/wsl.conf)
├── srv/mios/                      # Data served by the system
│   └── api/                       # Sample OpenAI v1 API payloads
├── var/                           # Mostly tmpfiles-declared placeholders
│   └── lib/mios/
│       ├── embeddings/            # RAG: chunks.jsonl, vector_store.import.jsonl, ingest_local.py
│       ├── training/              # Fine-tune datasets (sft.jsonl, dpo.jsonl)
│       └── evals/                 # OpenAI Evals API artifacts
├── usr/share/mios/prompts/              # XML-structured prompt templates
├── tools/                         # Repo-internal dev/operator tooling
│   ├── lib/                       # Shared helpers (path-refactor.py, ascii-sweep.py,
│   │                              #   quote-mios.py, install-env.ps1, userenv.sh,
│   │                              #   generate-sbom.py)
│   ├── *.sh / *.py / *.ps1        # Operator-runnable scripts (preflight, vfio,
│   │                              #   profilers, etc.)
│   └── windows/                   # Windows-specific helpers
├── config/
│   ├── artifacts/                 # BIB configs (bib.toml, iso.toml, qcow2.toml,
│   │                              #   vhdx.toml, wsl2.toml)
│   └── bootstrap/bootstrap.ps1    # Windows bootstrap PS1
├── Containerfile                  # OCI build entry (single-stage + ctx scratch)
├── Justfile                       # Linux build orchestrator
├── mios-build-local.ps1           # Windows build orchestrator
├── install.ps1                    # Unified Windows installer (build + WSL deploy)
├── Get-MiOS.ps1                   # Bootstrap-from-irm-iex entry point
├── preflight.ps1 / preflight.sh   # Prerequisite checks
├── push-to-github.ps1             # CI helper
├── *.md                           # README, CLAUDE, GEMINI, AGENTS, INDEX,
│                                  #   ARCHITECTURE, ENGINEERING, SECURITY,
│                                  #   DEPLOY, SELF-BUILD, CONTRIBUTING,
│                                  #   LICENSES, INSTALL, API, SOURCES,
│                                  #   MiOS-Engineering-Reference (this file),
│                                  #   CLAUDE.AUDIT, MiOS-SBOM (CSV)
└── VERSION                        # Single line: "v0.2.x"
```

### `mios-bootstrap` repo (installer layer) -- sibling root overlay

```
.
├── bootstrap.sh / bootstrap.ps1   # Phase-0 entry (preflight + identity capture)
├── install.sh / install.ps1       # Phase-1 total root merge + Phase-3 user create
├── identity.env.example           # Template for the identity envelope
├── image-versions.yml             # Renovate-managed version pins
├── etc/mios/profile.toml          # Host vendor profile
├── etc/skel/.config/mios/         # Per-user seed files
├── usr/share/mios/ai/             # Bootstrap AI seed (system.md, v1/)
├── usr/share/mios/user-preferences.md  # JSON-embedded user-preferences card
├── profile/                       # Profile staging area
└── *.md                           # README, AI, IMPLEMENTATION-SUMMARY,
                                   #   USER-SPACE-GUIDE, VARIABLES, system-prompt
```

---

## §2. Base image and supply chain

### Primary base
- **`ghcr.io/ublue-os/ucore-hci:stable-nvidia`** (Containerfile:2 -- `ARG BASE_IMAGE`).
- Resolved digest captured per build by `automation/build.sh` via `record_version`
  (`automation/lib/common.sh`).

### Alternate bases (build-arg selectable)
- `ghcr.io/ublue-os/ucore-hci:stable` (no NVIDIA).
- `ghcr.io/ublue-os/ucore:stable` (minimal uCore, no HCI extras).

### Renovate
- `renovate.json` at repo root; tracks Containerfile FROM lines, Quadlet
  `Image=` refs, and image-versions.yml entries.

### External OCI images (Quadlet sidecars)
| Image | Quadlet |
|---|---|
| `docker.io/localai/localai:latest` | `etc/containers/systemd/mios-ai.container` |
| `quay.io/ceph/ceph:latest` | `etc/containers/systemd/mios-ceph.container` |
| `docker.io/rancher/k3s:latest` | `etc/containers/systemd/mios-k3s.container` |
| `docker.io/ollama/ollama:latest` | `usr/share/containers/systemd/ollama.container` |
| `docker.io/crowdsecurity/crowdsec:latest` | `usr/share/containers/systemd/crowdsec-dashboard.container` |
| `docker.io/guacamole/guacamole:latest` | `usr/share/containers/systemd/mios-guacamole.container` |
| `docker.io/guacamole/guacd:latest` | `usr/share/containers/systemd/guacd.container` |
| `docker.io/library/postgres:latest` | `usr/share/containers/systemd/guacamole-postgres.container` |
| `quay.io/poseidon/matchbox:latest` | `usr/share/containers/systemd/mios-pxe-hub.container` |

### Build-time tools
| Image | Purpose | Where |
|---|---|---|
| `quay.io/centos-bootc/bootc-image-builder:latest` | RAW/ISO/QCOW2/VHDX/WSL2 disk images | `MIOS_BIB_IMAGE` in `Justfile` + `config/artifacts/*.toml` |
| `quay.io/centos-bootc/centos-bootc:stream10` | rechunk fallback | `MIOS_IMG_RECHUNK` in `mios-build-local.ps1` |
| `anchore/syft:latest` | CycloneDX/SPDX SBOM | `automation/90-generate-sbom.sh` + `Justfile` `sbom` target |
| `docker.io/library/alpine:latest` | helper-image fallback | `mios-build-local.ps1` |

### Cosign keyless signing
- Workflow: `.github/workflows/mios-ci.yml`.
- Keyless OIDC: `cosign sign --yes <image-digest>`; trust roots in
  `etc/containers/policy.json` + `automation/42-cosign-policy.sh`.
- Cosign v2 binary downloaded by `automation/42-cosign-policy.sh`.

### LAW 3: BOUND-IMAGES
Every Quadlet `Image=` ref is symlinked into
`usr/lib/bootc/bound-images.d/<container-name>.container` so bootc
fetches the image alongside the host on every `bootc upgrade`. Binder loop
in `automation/08-system-files-overlay.sh:74-86`.

---

## §3. Build pipeline

### Containerfile shape (single-stage + ctx scratch)
```
FROM scratch AS ctx                 # build context staging
COPY automation/ usr/ etc/ ... → /ctx/
COPY usr/share/mios/PACKAGES.md → /ctx/PACKAGES.md
COPY VERSION                      → /ctx/VERSION
COPY config/artifacts/            → /ctx/bib-configs/
COPY tools/                       → /ctx/tools/

FROM ${BASE_IMAGE}                  # main build stage
LABEL ...
CMD ["/sbin/init"]
ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=
RUN --mount=type=bind,from=ctx,...
    --mount=type=cache,...
    set -ex;
    cp -a /ctx/* /tmp/build/;
    install_packages_strict base;            # Containerfile pre-pipeline
    bash /tmp/build/automation/08-system-files-overlay.sh;  # overlay
    /tmp/build/automation/build.sh;          # phase-script orchestrator
    dnf clean all;
    rm -rf /tmp/build;
    find /var ! -name tmp ! -name cache -delete;
    find /run ! -name secrets -delete
RUN bootc completion bash > /etc/bash_completion.d/bootc
RUN bash /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source || true
RUN ostree container commit
RUN bootc container lint            # LAW 4 (FINAL RUN)
```

### Phase script table (`automation/[NN]-*.sh`)

`automation/build.sh` iterates every numbered script in lex order. Per-script
`set +e`/`set -e` wrapping (`automation/build.sh:234-237`) captures failures
into `FAIL_LOG`/`WARN_LOG` instead of aborting. Critical packages
post-validated via `rpm -q` against `packages-critical` from `PACKAGES.md`
(`automation/build.sh:285-300`).

| # | Script | Purpose |
|---|---|---|
| 01 | 01-repos.sh | RPMFusion + Terra + dnf-plugins-core + dnf5-plugins repo setup |
| 02 | 02-kernel.sh | kernel-modules-extra/devel/headers/tools (no kernel upgrade) |
| 05 | 05-enable-external-repos.sh | Terra + nvidia-container-toolkit + Microsoft repos |
| 08 | 08-system-files-overlay.sh | usr/+etc/ overlay; bound-images binder loop |
| 10 | 10-gnome.sh | GNOME 50 + Bibata cursor + Phosh |
| 11 | 11-hardware.sh | mesa + AMD ROCm + Intel + NVIDIA akmod |
| 12 | 12-virt.sh | KVM/QEMU + libvirt + Looking Glass build deps |
| 13 | 13-ceph-k3s.sh | Ceph client + k3s binary download |
| 18 | 18-apply-boot-fixes.sh | USBGuard perms + 203/EXEC chmod fix + 217/USER systemd-resolved fix |
| 19 | 19-k3s-selinux.sh | k3s-selinux policy compile (shipped, not loaded) |
| 20 | 20-fapolicyd-trust.sh | fapolicyd trust DB (initial seed) |
| 20 | 20-services.sh | Service preset/drop-in cleanup |
| 21 | 21-moby-engine.sh | moby-engine + buildx parity |
| 22 | 22-freeipa-client.sh | sssd + ipa-client (Day-2 enrollment optional) |
| 23 | 23-uki-render.sh | UKI artifact render via systemd-ukify |
| 25 | 25-firewall-ports.sh | firewalld permanent port set |
| 26 | 26-gnome-remote-desktop.sh | GNOME-RD enable; xrdp masked |
| 30 | 30-locale-theme.sh | Locale + dark theme (skel-based) |
| 31 | 31-user.sh | PAM authselect + sysusers user create |
| 32 | 32-hostname.sh | Default hostname template (`mios-XXXXX` derivable) |
| 33 | 33-firewall.sh | mios-firewall-init libexec + zone defaults |
| 34 | 34-gpu-detect.sh | mios-gpu-detect service bridge |
| 35 | 35-gpu-passthrough.sh | VFIO PCI passthrough kargs + binder rules |
| 35 | 35-gpu-pv-shim.sh | GPU paravirt shim |
| 35 | 35-init-service.sh | mios-init.service formal target transitions |
| 36 | 36-akmod-guards.sh | akmods.service condition gating |
| 36 | 36-tools.sh | Operator utility install (htop, jq, etc.) |
| 37 | 37-aichat.sh | aichat / aichat-ng binary download |
| 37 | 37-flatpak-env.sh | /usr/lib/mios/env.d/flatpaks.env capture |
| 37 | 37-ollama-prep.sh | Ollama prep (CI-skipped) |
| 37 | 37-selinux.sh | semanage booleans + fcontext rules |
| 38 | 38-vm-gating.sh | Hyper-V vsock + GNOME-RD setup |
| 39 | 39-desktop-polish.sh | Desktop entries + MOTD + fastfetch |
| 40 | 40-composefs-verity.sh | composefs verity for /usr immutability |
| 42 | 42-cosign-policy.sh | cosign v2 download + policy bake |
| 43 | 43-uupd-installer.sh | uupd Day-2 update path |
| 44 | 44-podman-machine-compat.sh | Podman-machine compatibility shim |
| 45 | 45-nvidia-cdi-refresh.sh | NVIDIA CDI generation timing |
| 46 | 46-greenboot.sh | greenboot health checks |
| 47 | 47-hardening.sh | secureblue-derived sysctl + kernel hardening |
| 49 | 49-finalize.sh | systemd preset-all + image metadata + cred scrub |
| 50 | 50-enable-log-copy-service.sh | mios-copy-build-log.service enable |
| 52 | 52-bake-kvmfr.sh | KVMFR kernel module bake |
| 53 | 53-bake-lookingglass-client.sh | Looking Glass B7 client bake (cmake/make) |
| 90 | 90-generate-sbom.sh | syft CycloneDX SBOM emission |
| 98 | 98-boot-config.sh | Boot config finalization |
| 99 | 99-cleanup.sh | Cache + tmp cleanup |
| 99 | 99-postcheck.sh | Build-time invariant validation (11 guards: see §15) |

Skipped under in-Containerfile build: `08-system-files-overlay.sh` (runs
pre-pipeline directly from Containerfile) and `37-ollama-prep.sh`
(CI-skipped -- too slow / network-heavy).

### Sub-phase numbering
The numeric prefix encodes execution order. Multiple scripts share a prefix
(20, 35, 36, 37, 99) when they're peer concerns at the same stage.

---

## §4. Software Bill of Materials

Single source of truth: `usr/share/mios/PACKAGES.md`. Every RPM must live in
a fenced ` ```packages-<category>` block parsed by
`automation/lib/packages.sh:get_packages` (regex
`/^\`\`\`packages-${category}$/,/^\`\`\`$/`).

Helpers (provided by `lib/packages.sh`):
- `install_packages "<category>"` -- best-effort, `--skip-unavailable`.
- `install_packages_strict "<category>"` -- fails the script on any miss.
- `install_packages_optional "<category>"` -- pure best-effort, never fails.

Categories and their counts (from `MiOS-SBOM.csv`):

| Category | Count | Purpose |
|---|---|---|
| repos | 5 | RPM repo enablement (no name installs) |
| base | 7 | Security stack, first-pass install (Containerfile pre-pipeline) |
| moby | 1 | moby-engine for Docker-API parity |
| uki | 1 | systemd-ukify for UKI builds |
| sbom-tools | 1 | syft |
| k3s-selinux-build | varies | SELinux policy build chain |
| kernel | 7 | kernel-modules-extra/devel/headers/tools |
| gnome | 39 | GNOME 50 desktop |
| gnome-core-apps | varies | GNOME core apps |
| gpu-mesa | 7 | Mesa userspace + Vulkan |
| gpu-amd-compute | varies | AMD ROCm |
| gpu-intel-compute | varies | Intel oneAPI / NEO |
| gpu-nvidia | 7 | NVIDIA proprietary stack |
| virt | 16 | KVM/QEMU + libvirt + Looking Glass build deps + KVMFR |
| containers | 33 | Podman, runc, conmon, netavark, slirp4netns, fuse-overlayfs |
| self-build | varies | The image's own build toolchain |
| boot | 9 | Bootloader, plymouth, grubby, dracut |
| cockpit | 13 | Cockpit web management |
| wintools | 6 | Windows VM tooling |
| security | 21 | SELinux, fapolicyd, USBGuard, audit, openscap, AIDE |
| gaming | 14 | Steam runtime, Proton, Lutris |
| guests | varies | Guest agents (virtio, spice) |
| storage | 18 | LVM, MD, multipath, ZFS, BTRFS, XFS |
| ceph | varies | Ceph client/server |
| k3s | varies | k3s prerequisites (binary downloaded separately) |
| ha | 15 | Pacemaker/Corosync |
| utils | 39 | Operator utilities |
| android | varies | Waydroid + binder |
| looking-glass-build | 23 | Looking Glass build chain |
| cockpit-plugins-build | varies | Cockpit plugin compilation |
| network-discovery | varies | mDNS, Avahi, SSDP, llmnr |
| phosh | varies | Phosh mobile session |
| updater | varies | uupd, BIB, rpm-ostree |
| freeipa | varies | FreeIPA / SSSD client |
| ai | varies | Local AI runtime |
| critical | 13 | Post-install rpm -q validation list |
| bloat | 7 | Removed packages |
| nut | varies | Network UPS Tools |

**Full enumeration: see [`MiOS-SBOM.csv`](MiOS-SBOM.csv) (373 entries).**

### Kernel rule (LAW-adjacent)
ONLY add: `kernel-modules-extra`, `kernel-devel`, `kernel-headers`,
`kernel-tools`. NEVER upgrade `kernel`/`kernel-core` in-container --
`automation/01-repos.sh:65,68` excludes them explicitly. dnf option spelling
is `install_weak_deps=False` (underscore); `install_weakdeps` is silently
ignored by dnf5.

---

## §5. From-source components

| Component | Build script | Source |
|---|---|---|
| **Looking Glass B7 client** | `automation/53-bake-lookingglass-client.sh` | git clone + cmake/make/install |
| **KVMFR kernel module** | `automation/52-bake-kvmfr.sh` | upstream gnif/LookingGlass tree |
| **k3s binary** | `automation/13-ceph-k3s.sh` | github.com/k3s-io/k3s releases (latest) |
| **k3s-selinux policy** | `automation/19-k3s-selinux.sh` | k3s-io/k3s-selinux |
| **Custom SELinux modules** | `usr/share/selinux/packages/mios/*.te` | Compiled per-rule, shipped, NOT loaded at build (loaded post-build via systemd) |
| **cosign v2** | `automation/42-cosign-policy.sh` | github.com/sigstore/cosign releases |
| **aichat / aichat-ng** | `automation/37-aichat.sh` | github.com/sigoden/aichat + blob42/aichat-ng |
| **Bibata cursor theme** | `automation/10-gnome.sh` | tarball download |

### LAW-relevant from-source policy
- Looking Glass + KVMFR build during `12-virt.sh` toolchain install; cmake/
  gcc/*-devel removed before image commit (image stays slim) -- see
  `automation/53-bake-lookingglass-client.sh:8`.
- SELinux modules ship as `.te` source AND compiled `.pp`; load happens
  at boot via `mios-selinux-init.service`, NOT during build (avoids
  composefs-verity breakage).

---

## §6. System overlay

### kargs.d (`usr/lib/bootc/kargs.d/*.toml`)

Flat array form only -- bootc rejects `[kargs]` section headers and `delete`
sub-keys.

| File | Kargs | Purpose |
|---|---|---|
| 00-mios.toml | `init=/sbin/init`, `audit=1`, `lockdown=integrity`, `iommu=pt`, `intel_iommu=on`, `amd_iommu=on` | Core boot / IOMMU |
| 01-mios-hardening.toml | `slab_nomerge`, `randomize_kstack_offset=on`, `vsyscall=none`, `oops=panic`, `module.sig_enforce=1` | Kernel hardening (note: `init_on_alloc/free` and `page_alloc.shuffle` deliberately disabled -- NVIDIA/CUDA incompatibility) |
| 02-mios-gpu.toml | NVIDIA/AMD/Intel GPU silicon-specific flags | Per-vendor GPU workarounds |
| 10-mios-verbose.toml | (commented-out by default) | Verbose boot for debugging |
| 10-nvidia.toml | `nvidia.NVreg_PreserveVideoMemoryAllocations=1` etc. | NVIDIA module overrides |
| 13-rtx50-vfio-workaround.toml | `pcie_acs_override=...`, RTX 50 idle workarounds | Blackwell VFIO/idle fix |
| 15-rootflags.toml | `rootflags=...` | Root mount options |
| 20-vfio.toml | `vfio-pci.ids=...` (placeholder) | VFIO passthrough |
| 30-security.toml | secureblue-derived flags | Extended hardening |
| 31-secureblue-extended.toml | additional secureblue kargs | Extended secureblue |

### sysctl.d (`usr/lib/sysctl.d/*.conf`)
- `90-mios-le9uo.conf` -- BORE/le9uo scheduler tuning (keys prefixed `-` so
  missing-on-vanilla kernels is silent).
- `90-mios-overlayfs.conf` -- overlay/sysext tuning.
- `99-mios-hardening.conf` -- TCP/IP hardening + `unprivileged_userns_clone`
  (also `-`-prefixed for kernel portability).

### modprobe.d (`usr/lib/modprobe.d/*.conf`)
- `nvidia-open.conf` -- open kernel module flag (managed at /usr to prevent
  /etc state drift).
- `blacklist-vmw_vsock.conf` -- blacklists VMware vsock (conflicts with
  Hyper-V hv_sock).

### modules-load.d (`usr/lib/modules-load.d/mios.conf`)
```
ntsync       # Wine NT sync (kernel 6.10+; cosmetic warn on WSL2 6.6)
vfio-pci
hv_sock
ceph
rbd
```

### tmpfiles.d (`usr/lib/tmpfiles.d/*.conf`)
Every `/var/*` and `/run/*` directory used by 'MiOS' is declared here. Files:
`mios.conf`, `mios-backup.conf`, `mios-ceph.conf`, `mios-cpu.conf`,
`mios-crowdsec.conf`, `mios-freeipa.conf`, `mios-gpu.conf`, `mios-grd.conf`,
`mios-infra.conf`, `mios-iommu.conf`, `mios-ipa.conf`, `mios-k3s.conf`,
`mios-nfs.conf`, `mios-pxe.conf`, `mios-virtio.conf`, `mios-wsl2-hacks.conf`.

LAW 2 enforcement: build-time writes to `/var/` are forbidden. The overlay
step at `automation/08-system-files-overlay.sh:49-67` writes home dotfiles
to `/etc/skel/` and lets `systemd-sysusers` populate `/var/home/<user>/`
at first boot.

### sysusers.d (`usr/lib/sysusers.d/*.conf`)
Canonical: `10-mios.conf` -- declares `g mios 1000` (numeric GID lookup
required by `u mios 1000:mios`). Critical: login users MUST have fixed UIDs
≥ UID_MIN (1000). Auto-allocation (`-`) picks from the system range
(< 1000) and breaks logind/XDG_RUNTIME_DIR. Postcheck #8/#8b enforce.

Service users: `50-mios.conf` (mios-virt UID 800), `50-mios-services.conf`
(guacamole/guacd/postgres/pxe-hub/crowdsec/ollama 810-815),
`50-mios-gpu.conf` (kvm/video/render GIDs pinned), `50-mios-ai.conf`
(mios-ai service), `20-podman-machine.conf` (`g core 1001` + `u core 1001:core`).

### dracut
- `usr/lib/dracut/dracut-logger.sh` -- upstream dracut (Apache/GPL,
  Amadeusz Żołnowski) -- vendored unchanged.
- Module setup overrides under `usr/lib/dracut/modules.d/*` -- vendored
  as upstream.

---

## §7. Quadlet sidecars

### `etc/containers/systemd/mios-ai.container`
- **Image:** `docker.io/localai/localai:latest`
- **Network:** `mios.network` (bound 10.89.0.0/24)
- **Port:** 8080 → `http://localhost:8080/v1` (LAW 5)
- **Volumes:** `/srv/ai/models`, `/srv/ai/mcp`
- **Env:** `MIOS_AI_KEY`, `MIOS_AI_MODEL`
- **User/Group:** `mios-ai`/`mios-ai`

### `etc/containers/systemd/mios-ceph.container`
- **Image:** `quay.io/ceph/ceph:latest`
- **User/Group:** `root`/`root` (documented exception -- Ceph requires uid 0)

### `etc/containers/systemd/mios-k3s.container`
- **Image:** `docker.io/rancher/k3s:latest`
- **User/Group:** `root`/`root` (documented exception -- k3s requires uid 0)

### `usr/share/containers/systemd/mios-pxe-hub.container`
- **Image:** `quay.io/poseidon/matchbox:latest`
- **User/Group:** `mios-pxe-hub`/`mios-pxe-hub`
- **Conditions:** `!wsl, !container`

### `usr/share/containers/systemd/mios-guacamole.container`
- **Image:** `docker.io/guacamole/guacamole:latest`
- **User/Group:** `mios-guacamole`/`mios-guacamole`
- **After:** `guacamole-postgres.service`

### Other Quadlets
- `guacd.container`, `guacamole-postgres.container`,
  `crowdsec-dashboard.container`, `ollama.container`.

All MiOS-owned Quadlets follow LAW 6: declare `User=`, `Group=`,
`Delegate=yes` (documented exceptions: ceph + k3s only).

---

## §8. Systemd services

70+ MiOS-owned units across `usr/lib/systemd/system/`. Grouped:

### Targets (role hierarchy)
- `mios-firstboot.target` -- Wants= cdi-detect, libvirtd-setup, grd-setup
- `mios-desktop.target`, `mios-headless.target`, `mios-hybrid.target`
- `mios-k3s-master.target`, `mios-k3s-worker.target`, `mios-ha-node.target`

### Firstboot services
- `mios-wsl-firstboot.service` -- WSL2 user creation + hostname + passwd
- `mios-wsl-init.service` -- WSL2 boot init
- `mios-wsl-runtime-dir.service` -- `/run/user/<uid>/` fallback (LAW-style fallback for non-PAM session paths)
- `mios-grd-setup.service` -- GNOME Remote Desktop firstboot (TLS keygen)
- `mios-cdi-detect.service` -- CDI generation (gated stub today)
- `mios-libvirtd-setup.service` -- libvirtd firstboot
- `mios-firstboot.target` -- pulls the above together

### GPU services
- `mios-gpu-amd.service` -- AMD ROCm/KFD plumbing
- `mios-gpu-intel.service` -- Intel iGPU/i915/xe plumbing
- `mios-gpu-nvidia.service` -- NVIDIA module load + CDI ordering
- `mios-gpu-status.service` -- GPU passthrough status writer

### Service drop-ins (`*.service.d/`)
- `10-bare-metal-only.conf` -- `ConditionVirtualization=no` (corosync,
  crowdsec, multipathd, nfs-server, nvidia-powerd, osbuild-*, pacemaker,
  pcsd, smb, nmb, mios-ha-bootstrap)
- `10-mios-wsl2.conf` -- `ConditionVirtualization=!wsl` (avahi, cloud-*,
  greenboot-healthcheck, qemu-guest-agent, rpm-ostree-fix-shadow-mode,
  stratisd, systemd-homed, systemd-logind, virtlxcd, zincati)
- `10-mios-virt-gate.conf` -- virtualization gating (audit*, bootloader-update,
  ceph-bootstrap, chronyd, fapolicyd, firewalld, gdm, nvidia-powerd, tuned,
  usbguard, waydroid-container)
- `10-virt-gate.conf` -- applies to 'MiOS' units skipping in containers/WSL
- `10-mios-container-gate.conf` -- NetworkManager + systemd-resolved gating

### Timers
- `uupd.timer` (Day-2 updates)
- `podman-auto-update.timer`
- `mios-firstboot.timer` (one-shot via target)

---

## §9. Greenboot health checks

### Required (boot fails on failure)
- `usr/lib/greenboot/check/required.d/10-mios-role.sh` -- verify role applied

### Wanted (warn, don't fail)
- (Standard upstream Fedora-bootc + greenboot defaults)

### Failure handling
- `usr/lib/greenboot/fail.d/00-log-fail.sh` -- captures journalctl --failed
  to `/var/log/greenboot.fail` before rollback.

---

## §10. Security stack -- 10 layers

1. **Kernel kargs** (`usr/lib/bootc/kargs.d/*.toml`) -- `lockdown=integrity`,
   `slab_nomerge`, `randomize_kstack_offset=on`, `vsyscall=none`,
   `oops=panic`, `module.sig_enforce=1`. NOT: `init_on_alloc/free`,
   `page_alloc.shuffle` (NVIDIA incompat -- see `SECURITY.md`).
2. **sysctl** (`usr/lib/sysctl.d/99-mios-hardening.conf`) -- TCP/IP
   hardening, ASLR, ptrace_scope, dmesg_restrict.
3. **SELinux modules** (`usr/share/selinux/packages/mios/*.te`) -- per-rule
   custom modules; booleans + fcontexts via semanage in `37-selinux.sh`.
4. **fapolicyd** (`etc/fapolicyd/fapolicyd.rules`, `usr/lib/fapolicyd/`) --
   zero-trust deny-by-default; trust DB seeded in `20-fapolicyd-trust.sh`.
5. **CrowdSec** (crowdsec-bouncer Quadlet) -- sovereign IPS mode;
   firewall-bouncer wires to firewalld.
6. **USBGuard** -- deny-by-default device policy; permissions enforced via
   `automation/18-apply-boot-fixes.sh:13`.
7. **firewalld** -- default zone `drop`; service set in `33-firewall.sh`.
8. **Audit / AIDE / OpenSCAP** -- audit subsystem present; AIDE policy
   shipped; OpenSCAP profile bound to PCI-DSS / DISA-STIG.
9. **composefs verity** (`automation/40-composefs-verity.sh`) -- `/usr` is
   verity-sealed read-only; tampering detected at boot.
10. **TPM2 / Clevis + image signing** -- cosign keyless OIDC chain; MOK
    keys at `etc/pki/mios/mok.der` (public); private key encrypted in
    GitHub secret per `automation/generate-mok-key.sh`.

---

## §11. AI/Agent surface

- **Endpoint:** `http://localhost:8080/v1` (LAW 5: UNIFIED-AI-REDIRECTS).
- **Sidecar:** `etc/containers/systemd/mios-ai.container` (LocalAI v2.20.0 by default).
- **Vendor system prompt:** `/usr/share/mios/ai/system.md`.
- **Host override:** `/etc/mios/ai/system-prompt.md`.
- **Per-user override:** `~/.config/mios/system-prompt.md`.
- **MCP discovery:** `/usr/share/mios/ai/v1/mcp.json`.
- **Model metadata:** `/usr/share/mios/ai/v1/models.json`.
- **CLI:** `/usr/bin/mios` (Python; reads `MIOS_AI_ENDPOINT` env var,
  falls back to `http://localhost:8080/v1`; reads system prompt from
  `MIOS_SHARE_DIR/ai/v1/system.md`).
- **Memory:** `/var/lib/mios/ai/memory/<agent-id>/` (sqlite WAL).
- **Scratch:** `/var/lib/mios/ai/scratch/`.
- **Journal:** `/var/lib/mios/ai/journal.md` (append-only).
- **KB delivery:** `/usr/share/mios/kb/manifest.json` (FHS-compliant
  location after `proc/mios/` migration).
- **OpenAI tool schemas:** `/usr/lib/mios/tools/responses-api/*.json` +
  `/usr/lib/mios/tools/chat-completions-api/*.json`.
- **Structured output schemas:** `/usr/lib/mios/schemas/*.json`.
- **Sample API payloads:** `/usr/share/mios/api/{chat,responses,embeddings,
  batch.requests,mcp.tool}.{json,jsonl}`.
- **Sanitization tooling:** `tools/ascii-sweep.py` (typography + emoji
  scrub across `git ls-files`), `automation/99-postcheck.sh` checks
  #12-#14 (vendor-URL / Quadlet User= / bound-images-coverage lint).

---

## §12. Build modes and output targets

### 5 build modes
1. **CI (`.github/workflows/mios-ci.yml`)** -- build → rechunk on tag → cosign
   keyless sign → push to GHCR.
2. **Linux local (`Justfile`)** -- `just build` → `localhost/mios:latest`.
3. **Windows local (`mios-build-local.ps1`)** -- same, via rootful Podman
   machine on WSL2.
4. **Self-build** -- a running 'MiOS' host runs `just build` against the repo
   it shipped with. The image contains its own toolchain (`packages-self-build`).
5. **Bootstrap (mios-bootstrap repo)** -- Total Root Merge of `mios.git` +
   `mios-bootstrap.git` onto a bare Fedora host, then `just build` from there.

### Output targets (Justfile)

| Target | Output |
|---|---|
| `just build` | `localhost/mios:latest` (OCI image) |
| `just rechunk` | `${IMAGE_NAME}:${VERSION}` + `:latest` (5-10× smaller deltas) |
| `just raw` | `output/mios.raw` (RAW disk image, 80 GiB ext4 root) |
| `just iso` | `output/mios-installer.iso` (Anaconda installer) |
| `just qcow2` | `output/mios.qcow2` (QEMU; needs `MIOS_USER_PASSWORD_HASH`) |
| `just vhdx` | `output/mios.vhdx` (Hyper-V; needs `MIOS_USER_PASSWORD_HASH`) |
| `just wsl2` | `output/mios.wsl2.tar` (WSL2 import tarball) |
| `just sbom` | `artifacts/sbom/mios-sbom.json` (CycloneDX) |
| `just artifact` | Refresh AI manifests + UKB + Wiki docs |
| `just all-bootstrap` | build + rechunk + log to bootstrap repo |

---

## §13. CI/CD

`.github/workflows/mios-ci.yml`:

| Step | Action |
|---|---|
| 1 | Checkout `mios-dev/MiOS` |
| 2 | Lint: shellcheck (`SC2038` fatal), hadolint, TOML validate |
| 3 | `bootc container lint` (LAW 4) |
| 4 | `podman build` → ghcr.io/mios-dev/mios:`<sha>` |
| 5 | On tag: `rechunk` → `:${VERSION}` + `:latest` |
| 6 | cosign keyless OIDC sign (image-digest) |
| 7 | Push to GHCR (requires `packages: write` permission) |

---

## §14. Architectural Laws (verbatim from `INDEX.md`)

1. **USR-OVER-ETC** -- static config in `/usr/lib/<component>.d/`; `/etc/`
   is admin-override only. Documented exceptions are upstream-contract
   surfaces (`/etc/yum.repos.d/`, `/etc/nvidia-container-toolkit/`).
2. **NO-MKDIR-IN-VAR** -- every `/var/` path declared via
   `usr/lib/tmpfiles.d/*.conf`. Never write to `/var/` at build time.
   bootc forbids it; lint will fail.
3. **BOUND-IMAGES** -- every Quadlet image symlinked into
   `/usr/lib/bootc/bound-images.d/`.
4. **BOOTC-CONTAINER-LINT** -- must be the final `RUN` of `Containerfile`.
   No `--squash-all` (strips OCI metadata bootc needs).
5. **UNIFIED-AI-REDIRECTS** -- all agents target `MIOS_AI_ENDPOINT`
   (`http://localhost:8080/v1`). Vendor-hardcoded URLs are forbidden.
6. **UNPRIVILEGED-QUADLETS** -- every Quadlet declares `User=`, `Group=`,
   `Delegate=yes`. Documented root exceptions: `mios-ceph`, `mios-k3s`.

---

## §15. Known issues and footguns (15+ hard-won lessons)

1. **WSL2 wsl.conf is byte-naive** -- em-dashes (any multibyte char) shift
   its line counter and surface as bogus `Expected ' ' or '\n' in
   /etc/wsl.conf:N` errors. Postcheck #7 enforces strict ASCII.
2. **systemd-sysusers `u name -` allocates from system range** (< UID_MIN).
   logind then refuses to create `/run/user/<uid>/`, breaking dbus user
   session, dconf, Wayland session services. Pin login UIDs to 1000+.
   Postcheck #8 enforces.
3. **`u name UID:NUM` requires `g name NUM` first** -- sysusers won't
   auto-create the group. Without the `g` line, sysusers fails with
   "please create GID NUM" and the user is never created. Postcheck #8b.
4. **`/var/run` is a symlink to `/run`** -- systemd-tmpfiles rejects entries
   whose path component is `/var/run/...` ("Line references path below
   /var/run"). Use `/run/...` directly. Postcheck #9 enforces.
5. **`/proc/mios/` is non-FHS** -- original KB delivery shipped to
   `proc/mios/manifest.json` as a "synthetic /proc surface", but FHS 3.0
   defines /proc as the kernel virtual filesystem. Moved to
   `/usr/share/mios/kb/manifest.json` for compliance.
6. **`((VAR++))` is forbidden under `set -e`** -- bash exits 1 when the
   pre-increment value is 0. Use `VAR=$((VAR + 1))`.
7. **`--squash-all` strips bootc OCI metadata** -- never use it. bootc
   relies on layer metadata for upgrade deltas.
8. **`install_weakdeps` is silently ignored by dnf5** -- correct spelling
   is `install_weak_deps=False` (underscore).
9. **`init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` are
   incompatible with NVIDIA/CUDA** -- disable in 'MiOS' despite secureblue
   recommending them. See `SECURITY.md`.
10. **`lockdown=integrity` not `confidentiality`** -- confidentiality
    breaks too many 'MiOS' workloads (kexec, /dev/mem, suspend-to-disk).
11. **Never upgrade `kernel`/`kernel-core` in-container** -- bootc's
    composefs/UKI flow assumes the base-image kernel. Only add
    `kernel-modules-extra/devel/headers/tools`. `automation/01-repos.sh`
    excludes the upgrade.
12. **systemd-udev-settle is deprecated upstream** -- emits warnings
    forever. Replace with `systemd-udev-trigger.service` ordering.
13. **WSL2 kernel 6.6 lacks `ntsync`** -- modules-load.d entry generates a
    cosmetic "Failed to find module" warning. Bare-metal Fedora 6.10+ has
    it. Acceptable.
14. **PAM session not opened under `wsl -u root` + `su - mios`** -- logind
    skips creating `/run/user/<uid>/`, so dbus/dconf/Wayland session
    services break. `mios-wsl-runtime-dir.service` is the belt-and-suspenders
    fallback (creates the dir unconditionally on WSL2 boot).
15. **systemd-tmpfiles 'D' type with no argument is interpreted as
    "purge"** -- always specify the args field (`-` for default age) to
    avoid wiping pre-existing data.
16. **BIB requires `/tmp/mios-bib-output` (or whatever Linux path) to
    exist BEFORE `podman run -v`** -- crun returns ENOENT otherwise. The
    `mios-build-local.ps1` `Phase 3` step pre-creates it via
    `podman machine ssh`.
17. **Sysusers files run lexicographically; `10-` runs before unprefixed
    base-distro files** -- duplicate `g <name> <gid>` lines are tolerated
    if the GID matches; mismatch fails the user creation.
18. **systemd Description= field is UTF-8-aware but most other fields
    aren't** -- keep all unit file content ASCII-only outside Description=
    to avoid surprise. Postcheck #11 enforces via `systemd-analyze verify`.
19. **`'MiOS'` (capital) in JSON keys breaks single-quote-wrapping policy**
    -- quote-mios.py's regex skips bare-string-literal `"MiOS"` so
    identifier values are preserved. Without that exclusion the
    PowerShell `$WslName = "MiOS"` becomes `"'MiOS'"` and WSL imports a
    distro literally named `'MiOS'`.
20. **`init.mount: target is busy` on WSL2 shutdown** -- WSL2-specific quirk
    where /init can't be unmounted because the WSL relay process holds it.
    Cosmetic; not a 'MiOS' bug.

---

## §16. Component licenses

| Component | License | Notes |
|---|---|---|
| 'MiOS' proper (this repo) | Apache-2.0 | `LICENSE` |
| uCore-HCI base | Apache-2.0 | upstream |
| Fedora CoreOS base | various (mostly GPL/MIT) | upstream Fedora |
| Looking Glass B7 | GPL-2.0 | from-source build |
| KVMFR module | GPL-2.0 | from-source build |
| k3s | Apache-2.0 | binary download |
| k3s-selinux | Apache-2.0 | from-source build |
| cosign v2 | Apache-2.0 | binary download |
| LocalAI | MIT | OCI image |
| Ceph | LGPL-2.1 | OCI image |
| Bibata cursor theme | GPL-3.0 | tarball download |
| dracut-logger.sh | GPL-2.0 | vendored upstream (Amadeusz Żołnowski) |
| systemd | LGPL-2.1+ | upstream Fedora |
| All RPMs | per individual SPEC | see `LICENSES.md` for full audit |
| NVIDIA proprietary driver | NVIDIA Software License Agreement | redistributable per RPMFusion |
| Microsoft Mono / .NET firmware | various Microsoft licenses | optional install |

Full audit in `LICENSES.md` and `SOURCES.md`.

---

## §17. SBOM generation paths

- **CycloneDX**: `automation/90-generate-sbom.sh` runs `syft` against the
  in-build image. Output: `/usr/lib/mios/logs/mios-sbom.cyclonedx.json`.
- **SPDX**: same script with `-o spdx-json`. Output beside CycloneDX.
- **Justfile target**: `just sbom` runs `syft` against `localhost/mios:latest`
  on a deployed host or in CI.
- **Manual**: `MiOS-SBOM.csv` (this delivery) -- generated by
  `tools/lib/generate-sbom.py` from PACKAGES.md + Quadlet refs +
  from-source list + Flatpak defaults.

---

## §18. Variable conventions

All MiOS-owned env vars start with `MIOS_*`. Resolution chain:

1. `~/.config/mios/mios.toml` `[env]` table (per-user, highest priority)
2. `/etc/mios/install.env` (host install identity)
3. `/etc/mios/env.d/*.env` (admin drop-ins, alphabetical)
4. `/usr/share/mios/env.defaults` (vendor defaults, lowest priority)

Canonical vars (see `usr/share/mios/env.defaults`):

| Variable | Default | Purpose |
|---|---|---|
| `MIOS_VERSION` | `0.2.4` | Image version |
| `MIOS_DEFAULT_USER` | `mios` | Login user name |
| `MIOS_DEFAULT_HOST` | `mios` | Hostname |
| `MIOS_REPO_URL` | https://github.com/mios-dev/mios | System repo URL |
| `MIOS_BOOTSTRAP_REPO_URL` | https://github.com/mios-dev/mios-bootstrap | Bootstrap repo URL |
| `MIOS_IMAGE_NAME` | `ghcr.io/mios-dev/mios` | OCI image base name |
| `MIOS_IMAGE_TAG` | `latest` | OCI image tag |
| `MIOS_BASE_IMAGE` | `ghcr.io/ublue-os/ucore-hci:stable-nvidia` | Containerfile base |
| `MIOS_LOCAL_TAG` | `localhost/mios:latest` | Local build tag |
| `MIOS_BIB_IMAGE` | `quay.io/centos-bootc/bootc-image-builder:latest` | BIB |
| `MIOS_LOCALAI_VERSION` | `v2.20.0` | LocalAI sidecar |
| `MIOS_AI_ENDPOINT` | `http://localhost:8080/v1` | Inference endpoint (LAW 5) |
| `MIOS_AI_MODEL` | `qwen2.5-coder:7b` | Default chat model |
| `MIOS_AI_KEY` | `""` | API key (empty for local) |
| `MIOS_INSTALL_ENV` | `/etc/mios/install.env` | Host install env file |
| `MIOS_WSLBOOT_DONE` | `/var/lib/mios/.wsl-firstboot-done` | Sentinel |

Build-time path constants (`automation/lib/paths.sh` + runtime
`/usr/lib/mios/paths.sh`):

| Variable | Value |
|---|---|
| `MIOS_USR_DIR` | `/usr/lib/mios` |
| `MIOS_LOG_DIR` | `/usr/lib/mios/logs` |
| `MIOS_LIBEXEC_DIR` | `/usr/libexec/mios` |
| `MIOS_SHARE_DIR` | `/usr/share/mios` |
| `MIOS_ETC_DIR` | `/etc/mios` |
| `MIOS_VAR_DIR` | `/var/lib/mios` |
| `MIOS_MEMORY_DIR` | `/var/lib/mios/memory` |
| `MIOS_SCRATCH_DIR` | `/var/lib/mios/scratch` |
| `MIOS_BUILD_LOG` | `/usr/lib/mios/logs/mios-build.log` |
| `MIOS_BUILD_CHAIN_LOG` | `/usr/lib/mios/logs/mios-build-chain.log` |

---

## §19. Hardware targeting

### Supported topologies
- **AI workstation**: AMD/Intel CPU + NVIDIA dGPU (Blackwell RTX 50, Ada
  RTX 40, Ampere RTX 30) -- full CUDA + LocalAI on-host.
- **Hyperconverged**: Single-node Ceph + k3s + KVM + Looking Glass --
  passthrough one GPU to a Windows VM, retain another for the host.
- **Headless server**: AMD EPYC / Intel Xeon, no display, k3s-master role.
- **WSL2**: Windows host, no GPU passthrough (compute fallback to CPU).

### Specific silicon workarounds
- **RTX 50 Blackwell**: GB20*/GB10* detected at runtime by
  `usr/libexec/mios/role-apply` -- defaults to headless role to avoid VFIO
  reset bug; `13-rtx50-vfio-workaround.toml` adds idle-flush kargs.
- **NVIDIA**: open kernel module via `usr/lib/modprobe.d/nvidia-open.conf`.
- **AMD ROCm**: `/dev/kfd` + `/dev/dri/renderD*` permissions hardened in
  `mios-gpu-amd.service` (chgrp render, chmod 0660).
- **Intel iGPU/dGPU**: `i915` and `xe` drivers loaded; renderD128 access
  hardened in `mios-gpu-intel.service`.
- **Hyper-V Enhanced Session**: `mios-hyperv-enhanced.service` wires GNOME
  Remote Desktop over hv_sock vsock (replacing the deprecated xrdp path).

---

## §20. Quick-reference cheatsheet

```bash
# Build (Linux)
just preflight            # System prereq check
just build                # OCI -> localhost/mios:latest
just rechunk              # Day-2-friendly delta optimization
just iso / raw / qcow2 / vhdx / wsl2   # Disk images
just sbom                 # CycloneDX SBOM

# Build (Windows)
.\preflight.ps1
.\mios-build-local.ps1    # rootful podman + WSL2 + podman build

# User-space config
just init-user-space      # seed ~/.config/mios/mios.toml
just edit                 # $EDITOR ~/.config/mios/mios.toml
just show-env             # resolved MIOS_* vars

# Day-2
bootc upgrade             # pull latest, stage
bootc rollback            # revert to previous
sudo systemctl reboot

# Diagnostics
journalctl -u mios-firstboot.target
journalctl -u mios-wsl-runtime-dir.service
cat /var/lib/mios/role.active
mios "ask the local AI a question"

# AI surface
curl -s http://localhost:8080/v1/models | jq
curl -s http://localhost:8080/v1/chat/completions -d @usr/share/mios/api/chat.local.example.json -H 'Content-Type: application/json' | jq

# Repo overlay (sanity)
ls /usr/lib/mios/             # paths.sh, logs/
ls /usr/share/mios/            # PACKAGES.md, env.defaults, mios.toml.example, ai/, kb/
ls /etc/mios/                  # install.env, profile.toml, ai/, kb.conf.toml
ls /var/lib/mios/              # memory, scratch, embeddings/, training/, evals/
```

---

## Appendix A: FHS layout table

| Path | FHS character | bootc disposition | Source-of-truth in repo |
|---|---|---|---|
| `/usr` | Read-only, shareable | Immutable composefs mount; change = new OCI image | `usr/` overlaid by `automation/08-system-files-overlay.sh` |
| `/etc` | Host-specific config | 3-way merge overlay; admin edits survive upgrades | `etc/` |
| `/var` | Mutable, persistent | Fully writable; never replaced on upgrade | `usr/lib/tmpfiles.d/mios*.conf` (LAW 2) |
| `/srv` | Data served by the system | Persistent | `usr/lib/tmpfiles.d/mios.conf` |
| `/run` | Ephemeral runtime (FHS 3.0) | tmpfs; cleared at boot; never in image layers | -- |
| `/home` | User home directories | Persistent via `/var/home/<user>` + symlink | `usr/lib/sysusers.d/` |
| `/opt` | Add-on software packages | Used for `usr/share/mios/prompts/` | direct overlay |
| `/usr/local` | Local additions | `/usr/share/mios/cookbooks/` | direct overlay |

---

## Appendix B: Reconciliation against live repo state

### Stale references no longer present (pre-this-session)
- `~/.config/mios/env.toml`, `images.toml`, `build.toml`, `flatpaks.list`
  -- collapsed into single `mios.toml` (§18 chain). Legacy fallback in
  `tools/lib/userenv.sh` if `mios.toml` is absent.
- `~/.config/mios/profile.toml` -- folded into `mios.toml [profile]`.
- `~/.config/mios/env` (bare shell-format) -- folded into `mios.toml [env]`.
- `proc/mios/manifest.json` -- moved to `usr/share/mios/kb/manifest.json`
  for FHS compliance. Self-references in the manifest content rewrote.
- `automation/install-fhs.sh` -- byte-identical to `automation/install.sh`,
  deleted.
- `system.md` (root) -- byte-identical to `system-prompt.md`, deleted.
  `system-prompt.md` is the canonical repo-root pointer (matches the
  override-layer naming `/etc/mios/ai/system-prompt.md` and
  `~/.config/mios/system-prompt.md`).
- `build-mios.sh` (root) -- near-duplicate of `automation/build-mios.sh`,
  deleted.
- `cloudws-pxe-hub.container`, `cloudws-guacamole.container` -- renamed to
  `mios-pxe-hub.container`, `mios-guacamole.container` for naming hygiene.

### Canonical naming map
| Old | New |
|---|---|
| CloudWS-bootc | 'MiOS' / mios-dev |
| CloudWS-OS | 'MiOS' / mios-dev |
| `cloudws-*.container` | `mios-*.container` |

The proper-noun spelling **`'MiOS'`** (single-quoted) is the legal-mark
form for display strings. Lowercase `mios` is the technical identifier
used in paths, env vars, package names, and code.

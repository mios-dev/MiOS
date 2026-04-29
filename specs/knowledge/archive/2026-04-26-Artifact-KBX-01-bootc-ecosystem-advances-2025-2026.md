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

# Bootc ecosystem advances MiOS should adopt now

**The bootc ecosystem has undergone transformative changes since v0.1.1**, with the composefs-native backend emerging as the single most consequential development—a full Rust reimplementation that will replace the OSTree backend and enable UKI-based measured boot. Universal Blue has simultaneously restructured into a modular OCI composition model, Fedora is converging all atomic variants onto bootc base images through its Image Mode Phase 2 initiative, and the merger of bootc-image-builder into image-builder-cli signals a maturing toolchain. For MiOS specifically, the most immediately actionable improvements are: adopting the new `bootc-base-imagectl rechunk` pipeline, implementing cosign keyless signing, migrating to logically-bound images for workload management, switching to NVIDIA open kernel modules with CDI, and incorporating SecureBlue's 29-parameter kernel hardening.

## The composefs-native backend rewrites bootc's foundation

The composefs-native backend tracked in bootc issue #1190 represents the project's most ambitious engineering effort across 2025–2026. This pure Rust reimplementation of composefs integrated directly into bootc will eventually retire the OSTree dependency entirely. Key milestones already landed include **SELinux enforcement for sealed composefs images** (v0.1.1, PR #2035), composefs garbage collection (PR #2040), and a new `bootc container ukify` command (v0.1.1, PR #1960) for creating Unified Kernel Images that link UKI to complete read-only filesystem trees.

The verification chain now works as follows: an OSTree commit includes `ostree.composefs.v0` metadata containing the composefs digest, signed with an Ed25519 key. During boot, the initrd validates the commit signature against a public key configured in `/usr/lib/ostree/prepare-root.conf`, then verifies the composefs digest matches. This creates a fully trusted read-only `/usr`. Configuration requires setting `[composefs] enabled = yes` (or `verity` to hard-require fsverity) in `prepare-root.conf`. MiOS should begin testing with `enabled = yes` now, with a path toward `verity` once the backend stabilizes.

Several critical composefs limitations remain. The `bootc rollback` command returns "This feature is not supported on composefs backend" — meaning production deployments should stay on the OSTree backend until rollback support lands. The `/etc` merge strategy (issues #1469, #1485) is still being implemented. However, **disk space pre-flight checks** (v0.1.1), fs-verity disabled install handling (PR #2004), and structured logging (PR #2032) have made the backend substantially more robust.

Beyond composefs, bootc v1.11.x–v0.1.1 delivered a wave of user-facing improvements. The **kargs.d system** now fully supports `/usr/lib/bootc/kargs.d/` TOML-format drop-in files with `match-architectures` filtering (PR #1783), enabling MiOS to ship per-architecture kernel arguments directly in its container image. Tag-aware upgrade operations (v0.1.1, PR #2094) let `bootc upgrade` understand container image tags. The `--bootloader none` install option (v0.1.1, PR #1997) supports systems without traditional bootloaders. Shell completions ship via RPM (PR #1938). And `bootc usroverlay --readonly` (v0.1.1, PR #2046) adds a new read-only overlay mode.

Soft reboot support—detecting SELinux policy deltas (PR #1768) and integrating with systemd's `soft-reboot.target`—dramatically reduces upgrade downtime. MiOS should implement `bootc upgrade --queue-soft-reboot` workflows once stabilized.

## Universal Blue's modular architecture and build innovations

Universal Blue executed a **massive 2025 refactoring from monolithic repos to modular OCI containers**. Bluefin now uses a three-tier OCI composition model: four shared OCI containers carry the project's "opinion," layered onto base OS images. Repositories split into `@projectbluefin/common` (desktop config), `@ublue-os/bluefin` (build system), `@ublue-os/brew` (Homebrew), and `@ublue-os/base-main` (base image). Build scripts are numbered `00-19` for execution order in `build_files/` directories—a pattern MiOS already follows. The Containerfile uses `COPY --from=` to assemble resources from multiple OCI containers in a context stage, which MiOS's `FROM scratch AS ctx` pattern can directly adopt.

The dependency management system centers on an **`image-versions.yml` manifest that pins all upstream images by SHA256 digest**, managed by Renovate Bot with 7-day stability periods and CODEOWNERS protection. MiOS should implement this exact pattern—create an `image-versions.yml`, configure Renovate with `docker:pinDigests` and automerge for digest updates, and protect the file via CODEOWNERS.

Bazzite's April 2026 update (kernel **v0.1.1**, Mesa **v0.1.1**) showcases several innovations MiOS should adopt. A brand-new rechunking engine is active, with Red Hat's **Chunkah** project (ZSTD compression) coming soon. SBOM-powered changelogs generate automated package diffs between builds. Build attestation is activated via cosign, and **OpenSSF Scorecard** scanning runs on every build. ISOs are now signed. Image size dropped ~1GB by moving optional components to DX variants.

The update system migrated from Python-based `ublue-update` (archived August 2025) to **uupd**, a Go-based unified update service that coordinates bootc, Flatpak (user + system), Distrobox, and Homebrew updates via systemd timers every 6 hours, with hardware checks for battery, CPU, memory, and network thresholds before proceeding.

For NVIDIA, Universal Blue ships **driver v0.1.1** (open) as default with **v0.1.1 LTS** available. Repository priorities are carefully ordered: Bazzite repos (1), Terra (3), Negativo17 (4), RPM Fusion (5). Critical packages including Mesa, PipeWire, and NetworkManager are locked via `dnf5 versionlock`. MiOS should adopt this version-locking strategy for its NVIDIA variants.

## Fedora's Image Mode Phase 2 converges all atomic variants

Fedora's Phase 2 initiative, documented at fedoraproject.org/wiki/Initiatives/Image_Mode,_Phase_2_(2026), aims to establish bootc-derived OCI artifacts as **first-class citizens** by Fedora 45. All atomic variants—CoreOS, IoT, Atomic Desktops—will consume shared base images built via a Konflux CI pipeline. Development pipeline targets Fedora 44; production pipeline targets Fedora 45. This convergence means MiOS's Fedora Rawhide base will benefit from the same infrastructure that powers CoreOS.

**Fedora 44 entered Beta on April 12, 2026** (final release April 14), shipping with Linux kernel 6.14, GNOME 48, systemd **259.5**, GCC **16.1**, glibc 2.43, Python 3.13, and **Podman 6**. DNF5 is the default package manager since Fedora 41, and Fedora 44 completes the transition by switching PackageKit to the DNF5 backend. The systemd 259.3 release (March 2026) patched a **critical local privilege escalation** (GHSA-6pwp-j5vg-5j6m), making it essential for MiOS to ensure it ships systemd ≥259.3.

Notable Fedora 44 changes relevant to MiOS include the **NTSYNC kernel module** for Wine/Steam gaming, unified boot loader updates via bootupd (phase 1), KMSCON replacing kernel FBCON, mkosi-initrd as an alternative initrd builder, and the drop of FUSE 2 libraries from Atomic Desktops. Fedora 43 made GNOME Wayland-only by removing X11 packages from repositories—GNOME upstream plans full X11 removal in GNOME 50. MiOS should verify all workflows function without X11 fallback.

## Image building tools converge toward a unified CLI

The bootc-image-builder (BIB) repository saw its last update on **December 15, 2025**, while `image-builder-cli` released v54 on March 18, 2026. The merger is progressing: both tools share substantial code, and the team plans to produce bootc artifacts directly in Fedora's Koji build system. MiOS should begin evaluating `image-builder-cli` alongside BIB for its VHDX, ISO, and raw image outputs.

Image-builder-cli brings several advantages: **SBOM generation** via `--with-sbom` (SPDX format), cross-architecture building via `--arch`, blueprint support in TOML/JSON, and no daemon requirement. It supports `dnf install image-builder` on Fedora or containerized use via `ghcr.io/osautomation/image-builder-cli:latest`.

Known BIB issues affecting MiOS include **ISO build failures when repos use `gpgkey=file://...`** (issue #1188, affects terra-mesa repo URLs), and GitHub Actions quirks where ubuntu-24.04 runners have overlay storage driver mismatches (issue #446). Bound images fail in BIB with a HOME directory lookup error (issue #715). The `osbuild-selinux` package must be installed on the build host for SELinux enforcing systems.

For ISO generation, Universal Blue's **Titanoboa** GitHub Action creates live ISOs from bootc container images, supporting squashfs (smaller) or erofs (faster boot) with hook scripts for pre/post rootfs customization. This may be more reliable than BIB's anaconda-iso path for MiOS.

## Security hardening brings defense-in-depth to immutable systems

SecureBlue's audit framework validates **50+ security checks** with status enums (PASS/INFO/WARN/FAIL/UNKNOWN) and actionable recommendations. MiOS should adopt their 29 validated kernel parameters, prioritizing the mandatory set:

- `init_on_alloc=1`, `init_on_free=1` — zero memory on allocation/free
- `slab_nomerge` — prevent slab cache merging
- `page_alloc.shuffle=1` — randomize page allocator freelists
- `randomize_kstack_offset=on` — randomize kernel stack offsets
- `vsyscall=none` — disable legacy vsyscall table
- `lockdown=confidentiality` — kernel lockdown mode

Additional SecureBlue techniques include replacing sudo with systemd's **`run0`** for privilege escalation, installing **hardened_malloc** from GrapheneOS (including within Flatpaks), enabling USBGuard with auto-generated device policies, DNS-over-TLS via configurable providers, MAC address randomization, and making bash initialization files immutable. The Trivalent browser (renamed from hardened-chromium) provides a hardened browsing experience.

For image signing, **cosign keyless signing with GitHub OIDC** is now the standard approach. The workflow requires `id-token: write` permission in GitHub Actions, uses Fulcio for short-lived certificates and Rekor for the transparency log, and signs by digest (`@sha256:...`) rather than tag. Universal Blue's builds fail without signing—MiOS should adopt the same enforcement. Container policies at `/etc/containers/policy.json` can verify signatures using `ostree-image-signed:docker://` prefixed references.

The confidential computing integration roadmap, demonstrated at CCC All Systems Go 2025, chains bootc → composefs → UKI → measured boot → remote attestation via the trustee project. AMD SEV-SNP (4th-gen EPYC) and Intel TDX (5th-gen Xeon) are supported with ~10% performance overhead. This is future work for MiOS but worth tracking.

## Container runtime and GPU management mature significantly

**Podman Quadlets** are now the flagship deployment mechanism. Podman 5.6 (August 2025) introduced the `podman quadlet` management subcommand. New unit types include `.build` and `.artifact` (both experimental). For bootc systems, distribution-defined quadlets belong at `/usr/share/containers/systemd/`; sysadmin overrides at `/etc/containers/systemd/`. The `AutoUpdate=registry` directive with `Notify=healthy` and `HealthCmd` enables automatic rollback on failed updates—a pattern MiOS should adopt for all containerized workloads.

**Logically-bound images** are production-ready in RHEL 9/10 and represent the recommended approach for associating container workloads with the bootc system lifecycle. Unlike physically-bound images (embedded in base layers), logically-bound images update independently—bootc pulls them during `bootc upgrade` into dedicated storage at `/usr/lib/bootc/storage`, retains them during rollbacks, and garbage-collects when unreferenced. Implementation requires `.image` quadlet files symlinked from `/usr/lib/bootc/bound-images.d/`.

For NVIDIA, **open kernel modules are now the recommended default** for Turing and newer GPUs (RTX 20xx+). RTX 50xx (Blackwell) GPUs **require** open modules—proprietary modules are incompatible. The nvidia-container-toolkit v0.1.1 makes **CDI (Container Device Interface) the default mode**, with JIT CDI spec generation at container creation. GPU access in Podman is now `podman run --device nvidia.com/gpu=0` rather than the old `--runtime=nvidia` approach. MiOS-2 should migrate to CDI immediately.

Critical security fixes in nvidia-container-toolkit: **CVE-2025-23266** (Critical) and **CVE-2025-23267** (High) were fixed in v0.1.1+. MiOS must ship ≥v0.1.1. The `nvidia-cdi-refresh.service` automatically regenerates CDI specs on toolkit install, kernel module reload, and GPU hotplug events.

**systemd-sysext** has matured as a viable extension mechanism for bootc. The fedora-sysexts collection at extensions.fcos.fr provides pre-built extensions for Fedora CoreOS, Atomic Desktops, and bootc. TrueNAS SCALE 24.10+ uses sysext for NVIDIA driver management. Extensions are stored as EROFS/squashfs `.raw` images, activated at boot by `systemd-sysext.service`, and can be managed via `systemd-sysupdate` for automatic updates. MiOS could use sysext for optional developer tools that shouldn't bloat the base image.

## Community projects and build tooling offer proven patterns

**RHEL Image Mode** reached GA in RHEL 9.6+ and 10+, introducing **download-only mode** (RHEL 10.2, February 2026) that separates download from apply for controlled maintenance windows, and OpenSCAP integration via `oscap-im` for build-time security hardening. The **system-reinstall-bootc** tool enables converting existing package-mode RHEL systems to bootc—a technique MiOS could adapt for migration paths.

**TunaOS** demonstrates desktop bootc images across multiple enterprise Linux bases (AlmaLinux, CentOS, Fedora), validating the multi-base approach. **StillOS** built on AlmaLinux 10 targets mainstream consumers with a curated app store model. Both projects confirm that MiOS's two-variant strategy (Fedora Rawhide + uCore base) aligns with community direction.

For rechunking, `bootc-base-imagectl rechunk --max-layers 67` is now the standard command, splitting a monolithic bootc image into content-addressed layers grouped by RPM package ownership. Custom layer assignment uses the `user.component` extended attribute: `setfattr -n user.component -v "my-apps" /usr/bin/my-custom-app`. MiOS should integrate rechunking into its CI pipeline after the build step and before the push step.

The GitHub Actions CI pattern for bootc projects follows a proven pipeline: build → rechunk → sign → push → release. Universal Blue runs weekly GHCR cleanup workflows that delete images older than 90 days while keeping the 7 most recent per tag. Renovate Bot manages digest pins with `config:best-practices`, `docker:pinDigests`, and automerge for minor/patch/digest updates. Dependabot handles GitHub Actions ecosystem updates separately on a weekly schedule.

## Critical bugs and fixes MiOS must address

Several bugs directly impact MiOS deployments. The **bootc v0.1.1 mount point check regression** (fixed in v0.1.1) broke BIB compatibility for images without a separate `/boot` partition—ensure MiOS uses ≥v0.1.1. The **systemd 259.3 local privilege escalation** affects all Fedora systems running earlier systemd 259.x releases. SELinux relabeling race conditions during install were fixed in v0.1.1 (PR #2025). Non-ASCII paths in `/etc` caused tar remapping failures, fixed in v0.1.1 (PR #2073). The `bootc status --format=json` output corruption under lock contention was fixed in v0.1.1 (PR #1905).

For NVIDIA on Fedora, recurring patterns include drivers from RPM Fusion breaking for 1–2 days after updates, Secure Boot claiming the system doesn't support it after Fedora upgrades, and kernel module loading failures despite correct installation. Universal Blue mitigates these by baking drivers into the image with akmod-nvidia, version-locking critical packages, and providing a `bazzite-rollback-helper` tool.

## Conclusion

The bootc ecosystem is rapidly maturing toward a production-grade platform where composefs replaces OSTree, UKI enables measured boot, and Fedora converges all atomic variants onto shared bootc base images. MiOS should prioritize five immediate actions: implement `bootc-base-imagectl rechunk` in CI, adopt cosign keyless signing with build attestation, migrate NVIDIA handling to open kernel modules with CDI, deploy SecureBlue kernel hardening parameters via kargs.d TOML drop-ins, and set up Renovate Bot with `image-versions.yml` for digest-pinned dependency management. The shift from BIB to image-builder-cli, the composefs rollback limitation, and Fedora 44's Podman 6 transition are the key risks to monitor. Universal Blue's modular OCI composition model—with its three-tier layering, numbered build scripts, and uupd unified updater—provides the most complete reference architecture for MiOS to follow.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

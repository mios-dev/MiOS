# MiOS Licensing & Components
> **Infrastructure:** Unified Open-Source System Specification
> **License:** MIT (Core Logic) / Apache-2.0 (Pipeline)
---
# Component Licenses

MiOS provides a unified environment for FOSS and essential proprietary hardware/software components. By using MiOS, you acknowledge and accept the license terms of all included components.

## Third-Party Components

These components are included for hardware compatibility or specific workstation roles and are governed by their respective licenses.

| Component | License | Notes |
|-----------|---------|-------|
| NVIDIA GPU Driver (590+) | [NVIDIA Software License](https://www.nvidia.com/en-us/drivers/nvidia-license/) | Essential hardware firmware/drivers. |
| NVIDIA Container Toolkit | Apache 2.0 | Open source. CDI specs for Podman GPU access. |
| NVIDIA Persistenced | [NVIDIA License](https://www.nvidia.com/en-us/drivers/nvidia-license/) | GPU state management. |
| Steam | [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/) | User-initiated application. |
| Wine / DXVK | LGPL 2.1 | Windows compatibility layer. |
| VirtIO-Win ISO | [Red Hat License](https://github.com/virtio-win/virtio-win-pkg-automation/blob/master/LICENSE) | KVM guest drivers. |
| Geist Font | [OFL 1.1](https://github.com/vercel/geist-font/blob/main/LICENSE.TXT) | UI typography. |

## Open-Source Licenses (Major Components)

| Component | License |
|-----------|---------|
| Linux Kernel | GPL 2.0 |
| systemd | LGPL 2.1 |
| GNOME (Mutter, GTK, libadwaita) | GPL 2.0+ / LGPL 2.1+ |
| Mesa | MIT |
| Podman / Buildah / Skopeo | Apache 2.0 |
| bootc | Apache 2.0 |
| K3s | Apache 2.0 |
| Pacemaker / Corosync | GPL 2.0 |
| CrowdSec | MIT |
| Looking Glass | GPL 2.0 |
| Waydroid | GPL 3.0 |
| Gamescope | BSD 2-Clause |
| Ceph | LGPL 2.1 / 3.0 |
| Flatpak | LGPL 2.1 |
| Cockpit | LGPL 2.1 |
| ROCm | MIT / Various |
| fapolicyd | GPL 3.0 |
| USBGuard | GPL 2.0 |

## Firmware

"linux-firmware" and "microcode_ctl" include binary firmware blobs under various redistribution licenses. These are required for hardware functionality.

## Your Responsibilities

- **Steam**: User-level acceptance of the Steam Subscriber Agreement is required.
- **NVIDIA**: Drivers are included for hardware compatibility.
- **Flatpak apps**: Applications have their own licenses; check Flathub metadata.
- **VM guests**: Windows VMs require valid external licenses.

## SBOM

Each CI build generates an SPDX and CycloneDX Software Bill of Materials. SBOMs are attached to the OCI image via cosign.

---
### Bootc Ecosystem & Resources
- **Core:** [containers/bootc](https://github.com/containers/bootc) | [bootc-image-builder](https://github.com/osautomation/bootc-image-builder)
- **Upstream:** [ublue-os/main](https://github.com/ublue-os/main)
- **Project Repository:** [MiOS-DEV/MiOS-bootstrap](https://github.com/MiOS-DEV/MiOS-bootstrap)
---

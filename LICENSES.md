# MiOS component licenses

MiOS is Apache-2.0 (`LICENSE`). Bundled components retain their upstream
licenses; using MiOS implies acceptance of all of them.

## Third-party (hardware/firmware/proprietary)

| Component | License | Notes |
|---|---|---|
| NVIDIA GPU driver (590+) | [NVIDIA Software License](https://www.nvidia.com/en-us/drivers/nvidia-license/) | Hardware drivers/firmware |
| NVIDIA Container Toolkit | Apache-2.0 | CDI specs for Podman GPU access |
| NVIDIA Persistenced | NVIDIA License | GPU state management |
| Steam | [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/) | User-initiated |
| Wine / DXVK | LGPL-2.1 | Windows compatibility |
| VirtIO-Win ISO | [Red Hat license](https://github.com/virtio-win/virtio-win-pkg-automation/blob/master/LICENSE) | KVM guest drivers |
| Geist Font | [OFL-1.1](https://github.com/vercel/geist-font/blob/main/LICENSE.TXT) | UI typography |

## Major open-source components

| Component | License |
|---|---|
| Linux kernel | GPL-2.0 |
| systemd | LGPL-2.1 |
| GNOME (Mutter, GTK, libadwaita) | GPL-2.0+ / LGPL-2.1+ |
| Mesa | MIT |
| Podman / Buildah / Skopeo | Apache-2.0 |
| bootc | Apache-2.0 |
| K3s | Apache-2.0 |
| Pacemaker / Corosync | GPL-2.0 |
| CrowdSec | MIT |
| Looking Glass | GPL-2.0 |
| Waydroid | GPL-3.0 |
| Gamescope | BSD-2-Clause |
| Ceph | LGPL-2.1 / LGPL-3.0 |
| Flatpak | LGPL-2.1 |
| Cockpit | LGPL-2.1 |
| ROCm | MIT and others |
| fapolicyd | GPL-3.0 |
| USBGuard | GPL-2.0 |

## Firmware

`linux-firmware` and `microcode_ctl` ship binary blobs under various
redistribution licenses. Required for hardware functionality.

## User obligations

- **Steam** — Steam Subscriber Agreement applies on first launch.
- **NVIDIA** — drivers shipped under NVIDIA Software License.
- **Flatpak apps** — each Flathub app has its own license metadata.
- **Windows VM guests** — bring your own valid licenses.

## SBOM

Every CI build emits CycloneDX (JSON) and SPDX (tag-value) SBOMs via
`syft` (`automation/90-generate-sbom.sh`). SBOMs are attached to the OCI
image via cosign attestation.

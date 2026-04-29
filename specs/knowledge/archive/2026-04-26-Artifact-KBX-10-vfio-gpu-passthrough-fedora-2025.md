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

# Linux VFIO GPU passthrough tools remain mostly unpackaged in 2025

**No single, polished application exists in Fedora's official repositories for dynamically managing GPU passthrough.** The ecosystem relies overwhelmingly on community shell scripts, libvirt hooks, and a handful of COPR-packaged tools. The most notable exception is **`driverctl`**, a Red Hat-developed utility available via `dnf install driverctl` that manages persistent driver overrides through udev and systemd. For dynamic, on-the-fly GPU switching with a proper D-Bus daemon, **`supergfxctl`** (available via Fedora COPR) is the closest thing to a turnkey solution, offering a dedicated VFIO mode that unbinds your GPU from nvidia/amdgpu and binds it to vfio-pci. Everything else — from libvirt hook scripts to GUI wrappers — lives on GitHub and must be manually installed.

## driverctl is the only VFIO-relevant tool in official Fedora repos

The single most important packaged tool for VFIO on Fedora is **`driverctl`**, developed originally for RHEL and available directly via `sudo dnf install driverctl`. It provides clean, persistent driver binding through udev rules and systemd integration:

```bash
driverctl set-override 0000:01:00.0 vfio-pci    # bind GPU to vfio-pci
driverctl set-override 0000:01:00.1 vfio-pci    # bind GPU audio too
driverctl unset-override 0000:01:00.0            # restore original driver
```

This persists across reboots automatically. VFIO expert Heiko Sieger recommends it as the preferred "method 1" for GPU driver binding on Fedora/RHEL systems. The limitation is that driverctl handles **boot-persistent** binding — it does not dynamically tear down a running display session to free a GPU mid-session. For that, you need hooks or supergfxctl.

Beyond driverctl, official Fedora repos provide the standard virtualization stack: **`libvirt`** and **`libvirt-client`** (which includes `virsh nodedev-detach` / `virsh nodedev-reattach` for on-demand VFIO binding), **`virt-manager`** (GUI for assigning PCI devices to VMs), **`cockpit-machines`** (web UI for host device assignment), **`edk2-ovmf`** (UEFI firmware required for GPU passthrough), and **`virglrenderer`** (paravirtualized OpenGL, a non-passthrough alternative). None of these handle the host-side GPU driver unbind/rebind workflow.

## supergfxctl delivers dynamic VFIO switching via D-Bus

**`supergfxctl`** from the ASUS Linux project is the most capable runtime GPU switching tool with explicit VFIO support. Written in Rust, it runs as a systemd daemon exposing a D-Bus interface for mode switching. Originally built for ASUS ROG laptops, it now works on most hybrid GPU laptops (Lenovo Legion, MSI, Dell, HP confirmed). Installation on Fedora:

```bash
sudo dnf copr enable eyecantcu/supergfxctl
sudo dnf install supergfxctl
```

After enabling VFIO in `/etc/supergfxd.conf` (`"vfio_enable": true`), you switch modes with `supergfxctl -m Vfio`. The daemon automatically unloads nvidia/amdgpu drivers and binds the discrete GPU to vfio-pci. Switching from Hybrid to Integrated requires a session logout; switching from Integrated to VFIO is instant. **Nobara Linux ships supergfxctl pre-installed**, reflecting its status as the community's preferred dynamic switching tool.

GUI frontends exist as GNOME Shell extensions (**Super Graphics Control** by krst, **GPU-Switcher-Supergfxctl** by chikobara) and a **KDE Plasma widget** (`supergfxctl-plasmoid`, COPR: `jhyub/supergfxctl-plasmoid`). These place a GPU mode indicator in the desktop panel with click-to-switch functionality including the VFIO mode. Note that supergfxctl conflicts with envycontrol, optimus-manager, and system76-power — only one GPU switcher can be active.

**envycontrol**, the other popular GPU switching tool (COPR: `sunwire/envycontrol`), does **not** have a VFIO mode in its upstream version. A community fork (`firelightning13/envycontrol-vfio`) adds this capability but is not separately packaged.

## Libvirt hooks remain the de facto standard for desktop GPU passthrough

The most widely used approach for dynamic GPU detach/attach on desktop systems with a single GPU (or for any per-VM GPU switching) is the **libvirt qemu hook framework**. Libvirt calls `/etc/libvirt/hooks/qemu` at VM lifecycle events, enabling automatic GPU unbinding before a VM starts and rebinding after it stops.

The standard workflow, executed by hook scripts in `/etc/libvirt/hooks/qemu.d/<VM_NAME>/prepare/begin/` and `release/end/`, follows this sequence: stop display manager → unbind VT consoles → unbind EFI framebuffer → unload GPU kernel modules → bind GPU to vfio-pci → start VM. The reverse runs on VM shutdown. The **PassthroughPOST/VFIO-Tools** project on GitHub provides the canonical hook dispatcher script used by virtually every GPU passthrough guide, but it is **not packaged as an RPM** — installation is a single `wget` command.

Several well-maintained single-GPU passthrough projects provide ready-made hook scripts:

- **risingprismtv/single-gpu-passthrough** (GitLab) — includes an `install-hooks.sh` installer
- **QaidVoid/Complete-Single-GPU-Passthrough** (GitHub) — most comprehensive guide, covers NVIDIA and AMD
- **nreymundo/vm-single-gpu-passthrough** (GitHub) — well-templated with numbered scripts for ordered execution

A practical caveat from recent experience: Shane McD's November 2025 Fedora Kinoite GPU passthrough documentation found that **`virsh nodedev-detach` and `managed='yes'` can hang libvirtd** on certain NVIDIA configurations. The workaround is using `managed='no'` with direct sysfs manipulation (`echo "0000:01:00.0" > /sys/bus/pci/devices/0000:01:00.0/driver/unbind`) in hook scripts instead.

## Cockpit can assign devices but cannot manage VFIO binding

**cockpit-machines** (standard Fedora package) gained PCI host device passthrough support in **v253**. Through the web UI, you can click "Add host device," select the PCI tab, and assign GPUs to VMs. You can also remove passthrough devices. However, cockpit-machines handles only the **libvirt XML assignment** — it does not manage IOMMU setup, kernel parameters, driver unbinding, or vfio-pci binding. All host-side VFIO preparation must be done separately via CLI.

The Cockpit project maintains a **wiki feature page** for a "Hardware Devices" panel that would include IOMMU group visualization, VFIO bind/unbind controls, and SR-IOV management. As of early 2026, this remains a **design document** — the full feature has not been implemented. **No third-party Cockpit plugin** for VFIO management exists either.

## Looking Glass and specialized tools available via COPR

**Looking Glass B7** is actively maintained (copyright through 2026) and enables viewing a GPU-passthrough VM's display on the host without a physical monitor, using shared memory (IVSHMEM) for uncompressed framebuffer transfer. It is not in official Fedora repos but is available through COPR:

- **Client**: COPR `pgaskin/looking-glass-client` → `looking-glass-client` RPM
- **KVMFR kernel module**: COPR `hikariknight/looking-glass-kvmfr` → `akmod-kvmfr` RPM (auto-rebuilds with kernel updates via akmods)

Looking Glass complements GPU passthrough but does not handle VFIO binding itself.

**vfio-isolate** is a Python tool for CPU and memory isolation (cpuset partitioning, IRQ affinity masking, CPU governor control) when running passthrough VMs. It is **only available via PyPI** (`pip install vfio-isolate`, version **v0.1.1**) — no Fedora RPM or COPR exists. It does not handle GPU binding; it is used alongside passthrough to reduce host-to-VM latency. Development appears feature-complete but dormant (GitHub: spheenik/vfio-isolate, 95 stars).

**GPU Passthrough Manager** (uwzis/GPU-Passthrough-Manager) is a GTK GUI for toggling GPUs between default and VFIO drivers, but it only handles **boot-time configuration** via GRUB modification — no dynamic runtime switching. It is available on Arch's AUR but **not reliably packaged for Fedora** (a COPR repo exists at `steeleyeballsac1/gpu-passthrough-manager` but appears unmaintained). Users have reported GRUB corruption issues.

## Complete package reference for Fedora VFIO setups

| Package | Source | Install command | What it does |
|---|---|---|---|
| `driverctl` | Official Fedora repos | `dnf install driverctl` | Persistent driver override via udev/systemd |
| `libvirt-client` | Official Fedora repos | `dnf install @virtualization` | `virsh nodedev-detach/reattach` commands |
| `virt-manager` | Official Fedora repos | `dnf install virt-manager` | GUI for PCI device assignment to VMs |
| `cockpit-machines` | Official Fedora repos | `dnf install cockpit-machines` | Web UI for VM PCI device assignment |
| `edk2-ovmf` | Official Fedora repos | `dnf install edk2-ovmf` | UEFI firmware for GPU passthrough VMs |
| `supergfxctl` | COPR | `dnf copr enable eyecantcu/supergfxctl` | Dynamic GPU ↔ vfio-pci switching daemon |
| `looking-glass-client` | COPR | `dnf copr enable pgaskin/looking-glass-client` | VM framebuffer display on host |
| `akmod-kvmfr` | COPR | `dnf copr enable hikariknight/looking-glass-kvmfr` | KVMFR kernel module for Looking Glass |
| `vfio-isolate` | PyPI only | `pip install vfio-isolate` | CPU/memory isolation for VM performance |

For Fedora's dracut-based initramfs, VFIO module early loading requires creating `/etc/dracut.conf.d/vfio.conf` with `add_drivers+=" vfio vfio_iommu_type1 vfio_pci "` and regenerating with `dracut -f --regenerate-all`. As of kernel 6.2+, `vfio_virqfd` is folded into the base `vfio` module and should not be listed separately.

## Conclusion

The VFIO GPU passthrough tooling landscape on Fedora remains fragmented. **`driverctl`** is the hidden gem — it's the only official-repo tool purpose-built for driver binding management and integrates cleanly with Fedora's systemd/udev stack, though it handles persistent (not session-dynamic) binding. **`supergfxctl`** via COPR is the best option for dynamic runtime switching with proper D-Bus integration and desktop GUI extensions. For per-VM automatic GPU detach/attach, **libvirt hooks** from community projects like PassthroughPOST/VFIO-Tools remain the universal standard despite being unpackaged shell scripts. The gap between what Proxmox offers as an integrated passthrough UI and what Fedora desktop users must manually configure remains wide — there is no Cockpit plugin, no GNOME application, and no Fedora-native tool that handles the full VFIO lifecycle from IOMMU configuration through dynamic GPU switching to VM device assignment in a single interface.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

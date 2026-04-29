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

# MiOS-Build Unified Management System v0.1.1

## Complete Integrated Edition

A **single, comprehensive bash script** (4,500+ lines) that provides complete MiOS-Build management without any external dependencies. Everything is built-in.

---

## Features

### ðŸ” System Assessment
- Quick virtualization readiness check (30 seconds)
- IOMMU group analysis for GPU passthrough
- CPU topology detection (AMD X3D, Intel Hybrid aware)
- Full system profiling with exportable reports

### ðŸ“¦ MiOS-Build Installation (17 Phases)
- Desktop mode (GNOME + full virtualization)
- Headless mode (Cockpit + CLI)
- Minimal mode (just libvirt/QEMU)
- Automatic hardware detection
- Progress tracking and logging

### ðŸŽ® VFIO GPU Passthrough
- Multi-vendor support (NVIDIA, AMD, Intel Arc)
- Automatic bootloader detection (systemd-boot, GRUB, rEFInd)
- IOMMU group validation
- Initramfs configuration
- Helper scripts (vfio-verify, iommu-groups)

### âš¡ CPU Core Isolation
- AMD X3D optimized presets (V-Cache aware)
- Intel Hybrid architecture support
- Custom isolation specification
- Kernel parameter management
- systemd affinity configuration
- Immediate and persistent changes

### ðŸ”§ VM CPU Pin Manager
- List VMs with current pinning
- Interactive pinning configuration
- Libvirt hook installation
- Per-VM configuration files
- XML snippet generator

### âœ… Verification & Diagnostics
- Service status checks
- VFIO binding verification
- CPU isolation confirmation
- Permission validation
- Diagnostic report generation
- Troubleshooting workflows

---

## Installation

```bash
# Download or copy the script
chmod +x mios-full.sh

# Run interactively (recommended)
sudo ./mios-full.sh

# Or use direct commands
sudo ./mios-full.sh help
```

---

## Usage

### Interactive Mode (Main Menu)
```bash
sudo ./mios-full.sh
```

### Direct Commands
```bash
sudo ./mios-full.sh assess      # System assessment menu
sudo ./mios-full.sh install     # Installation menu
sudo ./mios-full.sh vfio        # Configure GPU passthrough
sudo ./mios-full.sh cpu         # Configure CPU isolation
sudo ./mios-full.sh vm          # VM CPU pin manager
sudo ./mios-full.sh verify      # Verify installation
sudo ./mios-full.sh diagnose    # Troubleshooting
sudo ./mios-full.sh status      # Quick status view
sudo ./mios-full.sh iommu       # View IOMMU groups
sudo ./mios-full.sh quick       # Quick assessment
sudo ./mios-full.sh logs        # View session logs
sudo ./mios-full.sh version     # Show version
```

---

## Main Menu Structure

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                          MAIN MENU                                        â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘   1) System Assessment              [Status indicator]                    â•‘
â•‘   2) MiOS-Build Installation          [Status indicator]                    â•‘
â• â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•£
â•‘  Post-Install Configuration                                               â•‘
â•‘   3) VFIO GPU Passthrough           [GPU isolation]                       â•‘
â•‘   4) CPU Core Isolation             [Performance]                         â•‘
â•‘   5) VM CPU Pin Manager             [Per-VM config]                       â•‘
â• â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•£
â•‘  Tools & Diagnostics                                                      â•‘
â•‘   6) Verify Installation            [Health check]                        â•‘
â•‘   7) Troubleshoot & Diagnose        [Fix issues]                          â•‘
â•‘   8) IOMMU Group Viewer             [GPU analysis]                        â•‘
â• â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•£
â•‘   s) System Status    l) Logs    h) Help    q) Quit                       â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

---

## Typical Workflow

### New Installation
1. **Assess** â†’ Run quick assessment to check compatibility
2. **Install** â†’ Choose Desktop/Headless/Minimal mode
3. **Reboot** â†’ Apply kernel changes
4. **VFIO** â†’ Configure GPU passthrough (if needed)
5. **CPU** â†’ Set up core isolation for VMs
6. **Verify** â†’ Confirm everything works

### Existing System
1. **Status** â†’ Check current state
2. **Configure** â†’ VFIO, CPU, or VM pinning as needed
3. **Verify** â†’ Validate configuration
4. **Diagnose** â†’ If issues arise

---

## File Locations

| Purpose | Location |
|---------|----------|
| Session logs | `/var/log/mios/session-*.log` |
| Debug logs | `/var/log/mios/debug-*.log` |
| State file | `/var/lib/mios/state.json` |
| Backups | `/var/lib/mios/backups/` |
| Libvirt hooks | `/etc/libvirt/hooks/qemu` |
| VM hook configs | `/etc/libvirt/hooks/qemu.d/*.conf` |
| VFIO config | `/etc/modprobe.d/vfio.conf` |

---

## State Tracking

The script maintains persistent state in `/var/lib/mios/state.json`:

```json
{
    "version": "v0.1.1",
    "install_phase": "completed",
    "install_mode": "desktop",
    "assessment_done": "true",
    "vfio_configured": "true",
    "cpu_isolated": "true",
    "vm_hooks_configured": "true",
    "looking_glass_installed": "false",
    "reboot_required": "false"
}
```

---

## AMD X3D CPU Optimization

The script includes special handling for AMD Ryzen X3D processors:

### Supported Models
- Ryzen 9 9950X3D (16 cores, 2 CCDs)
- Ryzen 9 7950X3D (16 cores, 2 CCDs)
- Ryzen 9 7900X3D (12 cores, 2 CCDs)
- Ryzen 7 5800X3D (8 cores, 1 CCD)

### Presets
- **Gaming Optimized**: VM gets CCD0 (V-Cache) for maximum cache benefit
- **Multi-VM Balanced**: Cores spread across both CCDs
- **Host Priority**: More cores reserved for host

### CPU Layout Display
```
CPU Thread Layout:
     0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15   <- CCD0 (V-Cache)
    16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31   <- CCD1 (High Freq)

Legend: â–  CCD0 (V-Cache)  â–  CCD1 (High Freq)
```

---

## VFIO Configuration

### What Gets Configured
1. **Modprobe** (`/etc/modprobe.d/vfio.conf`)
   - Device IDs for VFIO-PCI binding
   - Softdeps for NVIDIA/AMD drivers

2. **Initramfs** (mkinitcpio or dracut)
   - VFIO modules loaded early

3. **Bootloader** (systemd-boot, GRUB, rEFInd)
   - IOMMU parameters
   - VFIO device IDs

### Helper Commands Created
```bash
vfio-verify    # Check VFIO configuration
iommu-groups   # Display IOMMU groups
```

---

## Libvirt Hooks

### Automatic CPU Isolation
When a VM starts:
- System processes moved to host CPUs
- VM gets dedicated isolated CPUs

When VM stops:
- If no other VMs running, full CPU access restored

### Per-VM Configuration
Create `/etc/libvirt/hooks/qemu.d/<vmname>.conf`:
```bash
HOST_CPUS="0,1,16,17"
VM_CPUS="2-15,18-31"
```

---

## Troubleshooting

### GPU Passthrough Not Working
```bash
sudo ./mios-full.sh diagnose
# Select: 1) GPU Passthrough Not Working
```

Common causes:
- IOMMU not enabled in BIOS
- vfio-pci not binding to device
- Conflicting drivers (nvidia, nouveau)

### VM Won't Start
```bash
sudo ./mios-full.sh diagnose
# Select: 2) VM Won't Start
```

Check:
- libvirt logs
- UEFI firmware presence
- Storage permissions

### Generate Diagnostic Report
```bash
sudo ./mios-full.sh diagnose
# Select: 5) Generate Full Diagnostic Report
```

Creates comprehensive report at:
`~/mios-diagnostic-TIMESTAMP.txt`

---

## Requirements

- **OS**: MiOS, Fedora Bootc, or Fedora-based distributions
- **Permissions**: Root (sudo)
- **Hardware**: 
  - CPU with virtualization extensions (AMD-V or Intel VT-x)
  - IOMMU support recommended (AMD-Vi or Intel VT-d)
  - GPU for passthrough (optional)
- **Network**: Required for installation phase

---

## What's Included (No External Scripts Needed)

| Feature | Lines | Description |
|---------|-------|-------------|
| Core infrastructure | ~500 | Colors, logging, state, utilities |
| System detection | ~400 | CPU, GPU, IOMMU, TPM, storage |
| Installation | ~600 | 17-phase MiOS-Build install |
| VFIO configuration | ~500 | GPU passthrough setup |
| CPU isolation | ~500 | Core isolation management |
| VM pinning | ~400 | Libvirt hooks and pinning |
| Verification | ~200 | Health checks |
| Diagnostics | ~300 | Troubleshooting tools |
| Menu system | ~600 | Interactive UI |
| **Total** | **~4,500** | Complete unified tool |

---

## Version History

### v0.1.1 - Integrated Edition
- Complete rewrite as unified script
- All functionality built-in (no external dependencies)
- AMD X3D CPU optimization
- Enhanced menu system
- Persistent state tracking
- Comprehensive logging
- Libvirt hook integration

---

## License

This tool is provided as-is for MiOS-Build users. Feel free to modify and distribute.

---

## Support

For issues or questions:
1. Run diagnostic report: `sudo ./mios-full.sh diagnose`
2. Check logs: `sudo ./mios-full.sh logs`
3. Review IOMMU groups: `sudo ./mios-full.sh iommu`

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

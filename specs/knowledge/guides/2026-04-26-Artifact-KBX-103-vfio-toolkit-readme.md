<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-fss/mios -->
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
> **Source Reference:** MiOS-Core-v0.1.4
---

# Universal VFIO PCIe Device Isolation Toolkit

A complete, production-ready toolkit for configuring **any PCIe device** for VFIO passthrough on Linux. Originally designed for RTX 4090 on MiOS/systemd-boot, now expanded to support any GPU vendor, any bootloader, and any Linux distribution.

## ðŸš€ Quick Start

```bash
# Run the universal configurator (interactive)
sudo ./universal-vfio-configurator.sh

# After reboot, verify configuration
./vfio-verify.sh
```

That's it! The script will guide you through device selection and configuration.

## ðŸ“¦ What's Included

| File | Purpose | Interactive? |
|------|---------|--------------|
| `universal-vfio-configurator.sh` | Main configuration script with device selection menu | âœ… Yes |
| `vfio-verify.sh` | Post-reboot verification and diagnostics | âŒ No |
| `rtx4090-vfio-isolation-guide.md` | Comprehensive manual with examples | ðŸ“– Reference |

## âœ¨ Universal Features

### Multi-Vendor GPU Support
- **NVIDIA**: GeForce, RTX, Quadro, Tesla, A100, H100
- **AMD**: Radeon RX, Pro, FirePro, Instinct
- **Intel**: Arc A-series, Data Center GPU Flex/Max
- **Any PCIe device**: Network cards, storage controllers, etc.

### Multi-Bootloader Support
- **systemd-boot** (MiOS, Arch, EndeavourOS)
- **GRUB / GRUB2** (Most distributions)
- **rEFInd** (Multi-boot systems)
- **Manual configuration** (Instructions provided)

### Multi-Initramfs Support
- **mkinitcpio** (Fedora-based distributions)
- **dracut** (Fedora, RHEL, openSUSE)

### Intelligent Device Detection
- Scans ALL PCIe devices (VGA, Display, Audio, USB)
- Auto-detects related devices in same IOMMU group
- Color-coded display by vendor (NVIDIA=Green, AMD=Red, Intel=Blue)
- Shows current driver binding and IOMMU group info

### IOMMU Group Analysis
- Visual representation of device isolation
- Warns about poor isolation (>5 devices in group)
- Suggests ACS override patch when needed
- Per-device IOMMU group membership display

## ðŸŽ® Common Use Cases

### 1. Gaming VM with GPU Passthrough
**Scenario**: Pass RTX 4090 to Windows 11 gaming VM, use integrated graphics for Linux host

```bash
sudo ./universal-vfio-configurator.sh
# Select: 1 2 (GPU + Audio)
# Reboot
# Configure VM in virt-manager
```

### 2. Multi-GPU Workstation
**Scenario**: Keep RTX 4090 for host workloads, pass older RTX 2080 Ti to VM

```bash
sudo ./universal-vfio-configurator.sh
# Select: 3 4 (older GPU + Audio)
# Keep primary GPU for host
```

### 3. AI/ML Development
**Scenario**: Pass NVIDIA A100 to Ubuntu ML VM while host uses AMD GPU

```bash
sudo ./universal-vfio-configurator.sh
# Select A100 device + related controllers
# Pin to specific NUMA node for optimal performance
```

### 4. Render Farm
**Scenario**: Multiple VMs, each with dedicated GPU for rendering

```bash
# Run script multiple times, once per GPU
# VM1: RTX 4090
# VM2: RTX 3090
# VM3: AMD RX 7900 XTX
```

### 5. Testing Environment
**Scenario**: Test GPU drivers/applications across different vendors

```bash
# Isolate secondary GPUs
# Create VMs: Windows 11, Ubuntu, Fedora
# Each VM gets different GPU vendor
```

## ðŸ“‹ Interactive Menu Example

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘ Available PCIe Devices
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ 1) VGA compatible controller: NVIDIA RTX 4090
â•‘    PCI: 01:00.0 â”‚ ID: 10de:2684 â”‚ IOMMU: 15
â•‘    Driver: nvidia
â• â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•£
â•‘ 2) Audio device: NVIDIA RTX 4090 Audio
â•‘    PCI: 01:00.1 â”‚ ID: 10de:22ba â”‚ IOMMU: 15
â•‘    Driver: snd_hda_intel
â• â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•£
â•‘ 3) VGA compatible controller: AMD Radeon RX 7900 XTX
â•‘    PCI: 0e:00.0 â”‚ ID: 1002:744c â”‚ IOMMU: 30
â•‘    Driver: amdgpu
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Selection Options:
  â€¢ Enter device numbers separated by spaces (e.g., 1 2 3)
  â€¢ Enter 'a' to select all devices
  â€¢ Enter 'q' to quit

Select devices for VFIO isolation: 1 2
```

## ðŸ”§ What the Script Does

### Phase 1: System Detection
- Detects CPU vendor (AMD/Intel) for correct IOMMU parameters
- Identifies bootloader (systemd-boot, GRUB, rEFInd)
- Determines initramfs system (mkinitcpio, dracut)
- Checks IOMMU initialization status

### Phase 2: Device Discovery
- Scans all PCIe devices (VGA, Display, Audio, USB)
- Displays interactive menu with color-coding
- Shows current driver, PCI address, device ID, IOMMU group
- Allows multi-select or single-select

### Phase 3: Related Device Detection
- Automatically finds devices in same IOMMU group
- Prompts to include related devices (recommended)
- Explains why related devices should be included

### Phase 4: IOMMU Analysis
- Visual display of IOMMU group membership
- Warns about large groups (poor isolation)
- Suggests ACS override patch if needed
- Shows all devices per group

### Phase 5: Configuration
- Creates `/etc/modprobe.d/vfio.conf` with vendor-specific softdep
- Updates initramfs configuration (modules + hook order)
- Modifies bootloader with kernel parameters
- Regenerates initramfs and updates bootloader

### Phase 6: Helper Scripts
- Installs `iommu-groups` command (view IOMMU topology)
- Installs `vfio-verify` command (post-reboot validation)

### Phase 7: Summary & Reboot
- Shows complete configuration summary
- Lists kernel parameters, files modified, rollback instructions
- Prompts for immediate reboot

## ðŸ›¡ï¸ Safety Features

### Automatic Backups
All modified files are backed up with timestamps:
- `/etc/modprobe.d/vfio.conf.backup-YYYYMMDD-HHMMSS`
- `/etc/mkinitcpio.conf.backup-YYYYMMDD-HHMMSS`
- `/boot/loader/entries/*.conf.backup-YYYYMMDD-HHMMSS`

### Rollback Support
```bash
# Restore from backup
sudo cp /etc/modprobe.d/vfio.conf.backup-20250114-153045 /etc/modprobe.d/vfio.conf
sudo cp /etc/mkinitcpio.conf.backup-20250114-153045 /etc/mkinitcpio.conf
sudo cp /boot/loader/entries/arch.conf.backup-20250114-153045 /boot/loader/entries/arch.conf
sudo mkinitcpio -P
sudo reboot
```

### Validation Checks
- Verifies IOMMU support before proceeding
- Checks bootloader existence
- Validates device selections
- Confirms initramfs regeneration success

## ðŸ“Š Verification After Reboot

```bash
# Run comprehensive verification
./vfio-verify.sh

# Manual checks
lspci -nnk -d 10de:2684    # Check specific device
ls -la /dev/vfio/           # Check VFIO device nodes
iommu-groups                # View all IOMMU groups
dmesg | grep -i vfio        # Check kernel messages
```

**Expected Output (Success):**
```
VFIO Configuration Verification
================================

Checking VFIO modules...
  âœ“ vfio loaded
  âœ“ vfio_pci loaded
  âœ“ vfio_iommu_type1 loaded

Checking device binding...
Device: 10de:2684
  Kernel driver in use: vfio-pci

VFIO device nodes:
  /dev/vfio/vfio
  /dev/vfio/15
```

## ðŸŽ¯ Advanced Configuration

### CPU Pinning (Ryzen 9950X3D Example)
For dual-CCD CPUs, pin VM to V-Cache CCD:

```xml
<vcpu placement='static'>16</vcpu>
<cputune>
  <vcpupin vcpu='0' cpuset='0'/>
  <vcpupin vcpu='1' cpuset='1'/>
  <!-- ... cores 2-15 ... -->
  <emulatorpin cpuset='16-23'/>
</cputune>
```

### Hugepages for Memory Performance
Add to kernel parameters:
```
default_hugepagesz=1G hugepagesz=1G hugepages=32
```

### ACS Override (Poor IOMMU Isolation)
If IOMMU groups contain many devices:
```
pcie_acs_override=downstream,multifunction
```

**Warning**: Reduces isolation security. Only use if necessary.

## ðŸ†˜ Troubleshooting

### GPU Still Bound to nvidia Driver
**Symptom**: `lspci -nnk` shows `nvidia` instead of `vfio-pci`

**Solutions**:
1. Check kernel parameters: `cat /proc/cmdline | grep vfio`
2. Verify module load order: `lsinitcpio /boot/initramfs-linux.img | grep -E '(vfio|nvidia)'`
3. Ensure modconf hook before kms: `grep "^HOOKS=" /etc/mkinitcpio.conf`
4. Rebuild initramfs: `sudo mkinitcpio -P`

### Code 43 in Windows VM
**Symptom**: NVIDIA driver fails with Code 43

**Solutions**:
1. Add to VM XML: `<kvm><hidden state='on'/></kvm>`
2. Add vendor_id: `<hyperv><vendor_id state='on' value='1234567890ab'/></hyperv>`
3. Disable Resizable BAR in BIOS
4. Pass through both GPU and audio device
5. Dump and pass VBIOS: See guide for instructions

### Black Screen on VM Start
**Symptom**: VM starts but no display output

**Solutions**:
1. Add kernel parameter: `video=efifb:off`
2. Ensure host isn't using the GPU (no X/Wayland)
3. Try different OVMF firmware variant
4. Check IOMMU group isolation

### Large IOMMU Groups
**Symptom**: Warning about >5 devices in group

**Solutions**:
1. Enable ACS override: `pcie_acs_override=downstream,multifunction`
2. Check BIOS settings for IOMMU granularity
3. Consider motherboard with better IOMMU support
4. Use AUR package: `linux-vfio` (includes ACS patch)

## ðŸ”— Integration with MiOS-Build

Add GPU passthrough phase to your MiOS-Build script:

```bash
# After Phase 4: VFIO GPU Isolation (Optional)
if ask_yes_no "Configure GPU for VFIO passthrough?"; then
    log_info "Launching Universal VFIO Configurator..."
    
    # Copy script if not present
    if [[ ! -f /usr/local/bin/universal-vfio-configurator.sh ]]; then
        cp ./universal-vfio-configurator.sh /usr/local/bin/
        chmod +x /usr/local/bin/universal-vfio-configurator.sh
    fi
    
    # Run configurator
    /usr/local/bin/universal-vfio-configurator.sh
fi
```

## ðŸ“š Resources

- [Arch Wiki - PCI Passthrough](https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF)
- [MiOS Wiki - QEMU Setup](https://wiki.cachyos.org/virtualization/qemu_and_vmm_setup/)
- [VFIO Subreddit](https://www.reddit.com/r/VFIO/)
- [Level1Techs VFIO Forum](https://forum.level1techs.com/c/software/vfio/11)

## ðŸ“ License

MIT License - Use freely for personal or commercial projects

## ðŸ¤ Contributing

Contributions welcome! Areas for improvement:
- Support for additional bootloaders (Limine, ZFSBootMenu)
- GUI frontend (GTK/Qt)
- Looking Glass integration
- Automatic VM creation with passed-through devices
- Single GPU passthrough with dynamic switching

## âš ï¸ Disclaimer

This toolkit modifies bootloader and kernel configurations. While extensive safety measures are implemented:
- **Always backup critical data** before proceeding
- Test in a non-production environment first
- Understand each step before running scripts
- Keep installation media available for recovery

The authors are not responsible for any system instability, data loss, or hardware issues resulting from the use of this toolkit.

---

**Made with â¤ï¸ for the VFIO community**

*Compatible with MiOS, Fedora Bootc, EndeavourOS, Manjaro, and any systemd-boot/GRUB-based distribution*

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-fss/mios](https://github.com/mios-fss/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-fss/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-fss/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

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

# MiOS-Build v0.1.1 - Looking Glass Integration

## What's New

The MiOS-Build installation script has been updated to version **v0.1.1** with full Looking Glass support for ultra-low latency GPU passthrough to Windows VMs!

### Key Changes

#### 1. **Upstream VirtIO ISO Integration**
- **Previous**: Used standard virtio-win ISO without IVSHMEM driver
- **New**: Downloads upstream virtio-win ISO (`v0.1.1`) that includes:
  - All standard VirtIO drivers for Windows 11
  - **IVSHMEM driver** required for Looking Glass shared memory
  - Latest Windows 11 24H2 driver support

**URL**: `https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/upstream-virtio/virtio-win-v0.1.1.iso`  
**Location**: `/var/lib/libvirt/images/virtio-win.iso`

#### 2. **Looking Glass Installation (Phase 15)**
New automated installation phase that:
- Installs all required dependencies (X11, Wayland, PipeWire, SPICE, etc.)
- Builds Looking Glass **B7** client from source
- Configures IVSHMEM device permissions via udev
- Creates shared memory device at `/dev/shm/looking-glass`
- Installs helper script: `looking-glass-start`

#### 3. **Enhanced Helper Scripts**
**`create-win11-vm`** now includes:
- Complete Looking Glass setup instructions
- IVSHMEM driver installation steps
- Shared memory XML configuration
- Recommended VM settings for optimal performance

**New: `looking-glass-start`**
```bash
# Simple launcher that waits for VM and starts Looking Glass client
looking-glass-start VM_NAME
```

#### 4. **Interactive Installation Prompt**
New prompt during installation:
```
Install Looking Glass for low-latency GPU passthrough? [Y/n]:
```
- Automatically enabled if IOMMU or NVIDIA GPU detected
- Can be declined for headless-only setups

---

## How Looking Glass Works

Looking Glass provides **near-native gaming performance** by:

1. **Shared Memory**: VM GPU framebuffer is copied to shared memory region
2. **IVSHMEM Device**: PCI device that both host and guest can access
3. **Zero-Copy Transfer**: Host client reads directly from shared memory
4. **No Network Overhead**: Unlike VNC/Spice, no compression or network latency

### Performance Benefits
- **<1ms latency** vs 20-50ms for Spice/VNC
- **Full refresh rates** (144Hz+ supported)
- **HDR support** (with compatible hardware)
- **No compression artifacts**

---

## Complete Setup Guide

### Prerequisites
âœ“ IOMMU enabled in BIOS  
âœ“ GPU passed through to VM  
âœ“ Windows 11 VM created  

### Step 1: Run MiOS-Build Installer
```bash
sudo ./mios-build.sh
```

When prompted:
- **Install Looking Glass?** â†’ Yes
- Script will build and configure everything automatically

### Step 2: Create Windows 11 VM
```bash
# Use the enhanced helper script
create-win11-vm

# Or use virt-install directly:
virt-install --name win11-gaming --memory 16384 --vcpus 12 \
  --os-variant win11 --boot uefi \
  --tpm backend.type=emulator,backend.version=2.0,model=tpm-tis \
  --disk size=100,bus=virtio,cache=writeback,io=threads \
  --cdrom /path/to/win11.iso \
  --disk /var/lib/libvirt/images/virtio-win.iso,device=cdrom \
  --network network=default,model=virtio \
  --graphics spice,listen=1.1.1.1 \
  --video qxl \
  --cpu host-passthrough,cache.mode=passthrough
```

### Step 3: Install Windows + VirtIO Drivers
During Windows installation:
1. When prompted for disk, click **"Load driver"**
2. Browse to virtio-win CD â†’ `vioscsi/w11/amd64` â†’ Install
3. Continue Windows installation normally
4. After first boot, install network driver: `NetKVM/w11/amd64`

### Step 4: Install IVSHMEM Driver (Critical!)
In Windows Device Manager:
1. Expand **System Devices**
2. Right-click **"PCI RAM Controller"** (yellow warning)
3. **Update driver** â†’ Browse my computer
4. Point to virtio-win CD: `Win10/amd64` folder
5. Install **"Red Hat IVSHMEM Device"** driver

### Step 5: Install Looking Glass Host
In Windows VM:
1. Download from: https://looking-glass.io/downloads
2. Run `looking-glass-host-setup.exe` as Administrator
3. **Important**: Enable "Start on boot" option
4. Restart Windows VM

### Step 6: Configure VM for Looking Glass
```bash
virsh shutdown win11-gaming
virsh edit win11-gaming
```

Add **before** `</devices>`:
```xml
<!-- Shared memory for Looking Glass -->
<shmem name='looking-glass'>
  <model type='ivshmem-plain'/>
  <size unit='M'>32</size>
</shmem>
```

**Memory size calculation:**
```
width Ã— height Ã— 4 Ã— 2 = bytes
bytes Ã· 1024 Ã· 1024 = MB (round up to power of 2)

Examples:
1920Ã—1080 â†’ 32 MB
2560Ã—1440 â†’ 64 MB  
3840Ã—2160 â†’ 128 MB
```

Also find and change:
```xml
<!-- Disable memory balloon for performance -->
<memballoon model='none'/>
```

Save and start VM:
```bash
virsh start win11-gaming
```

### Step 7: Start Looking Glass Client
```bash
# Wait for Windows to boot, then:
looking-glass-start win11-gaming

# Or manually:
looking-glass-client -F -f /dev/shm/looking-glass
```

---

## Advanced Configuration

### CPU Pinning for 9950X3D
For optimal gaming performance, pin VM to V-Cache CCD:

```xml
<vcpu placement='static'>12</vcpu>
<cputune>
  <!-- Pin to CCD0 physical cores (V-Cache) -->
  <vcpupin vcpu='0' cpuset='2'/>
  <vcpupin vcpu='1' cpuset='18'/>
  <vcpupin vcpu='2' cpuset='3'/>
  <vcpupin vcpu='3' cpuset='19'/>
  <vcpupin vcpu='4' cpuset='4'/>
  <vcpupin vcpu='5' cpuset='20'/>
  <vcpupin vcpu='6' cpuset='5'/>
  <vcpupin vcpu='7' cpuset='21'/>
  <vcpupin vcpu='8' cpuset='6'/>
  <vcpupin vcpu='9' cpuset='22'/>
  <vcpupin vcpu='10' cpuset='7'/>
  <vcpupin vcpu='11' cpuset='23'/>
  
  <!-- Reserve CCD1 cores for host -->
  <emulatorpin cpuset='8-15,24-31'/>
</cputune>
```

### Looking Glass Client Options
```bash
# Fullscreen with border removal
looking-glass-client -F

# Specific resolution
looking-glass-client -F -w 2560 -h 1440

# Enable SPICE audio forwarding
looking-glass-client -F -o audio:micDefault=allow

# VSync control
looking-glass-client -F -o win:vsync=yes

# All options
looking-glass-client --help
```

### Keyboard/Mouse Capture
- **Default capture key**: `Scroll Lock`
- **Release capture**: Press `Scroll Lock` again
- **Custom capture key**: `looking-glass-client -m KEY`

Common keybinds:
- `ScrollLock + Q`: Quit client
- `ScrollLock + F`: Toggle fullscreen
- `ScrollLock + I`: Input statistics
- `ScrollLock + V`: Video statistics

---

## Troubleshooting

### Issue: "Failed to open IVSHMEM device"
**Solution**: Ensure VM has shared memory device configured
```bash
virsh dumpxml win11-gaming | grep -A5 shmem
```

### Issue: IVSHMEM driver not in Device Manager
**Solution**: Check virtio-win ISO is upstream version with driver
```bash
ls -lh /var/lib/libvirt/images/virtio-win.iso
# Should be ~550MB for upstream, ~250MB for stable
```

### Issue: Looking Glass Host not starting
**Solution**: 
1. Check Windows Task Scheduler for "Looking Glass Host" task
2. Verify it's set to run at system startup
3. Manually run: `C:\Program Files\Looking Glass (host)\looking-glass-host.exe`

### Issue: Black screen or "Waiting for host..."
**Solution**:
1. Ensure Windows VM has booted completely
2. Check shared memory permissions: `ls -la /dev/shm/looking-glass`
3. Verify Looking Glass Host is running in Windows Task Manager
4. Check for GPU driver issues in Windows

### Issue: Poor performance or stuttering
**Solutions**:
- Increase shared memory size (see calculation above)
- Enable VSync: `-o win:vsync=yes`
- Pin VM CPUs to V-Cache cores
- Disable memory ballooning
- Use `cache=writeback` on disk
- Enable hugepages (see MiOS-Build documentation)

---

## Performance Comparison

| Feature | Looking Glass | Spice | VNC |
|---------|---------------|-------|-----|
| **Latency** | <1ms | 20-50ms | 50-100ms |
| **Refresh Rate** | 144Hz+ | 60Hz | 30-60Hz |
| **GPU Acceleration** | Full | Limited | None |
| **HDR Support** | Yes | No | No |
| **Network Required** | No | Yes | Yes |
| **Audio Sync** | Perfect | Good | Poor |

---

## Integration with Existing VMs

If you have existing VMs and want to add Looking Glass:

```bash
# 1. Update virtio drivers in Windows
# Mount the new upstream ISO in virt-manager

# 2. Install IVSHMEM driver (see Step 4 above)

# 3. Install Looking Glass Host in Windows

# 4. Add shared memory to VM XML
virsh edit VM_NAME
# (add <shmem> block)

# 5. Start Looking Glass client
looking-glass-start VM_NAME
```

---

## Files Created by Script

| Path | Description |
|------|-------------|
| `/usr/local/bin/looking-glass-client` | Looking Glass client binary |
| `/usr/local/bin/looking-glass-start` | Helper script to launch client |
| `/etc/udev/rules.d/99-kvmfr.rules` | KVMFR device permissions |
| `/etc/tmpfiles.d/10-looking-glass.conf` | Shared memory device config |
| `/var/lib/libvirt/images/virtio-win.iso` | Upstream VirtIO + IVSHMEM drivers |

---

## Resources

- **Looking Glass**: https://looking-glass.io/
- **Documentation**: https://looking-glass.io/specs/
- **Discord**: https://discord.gg/52SMupxkvt
- **Upstream VirtIO Drivers**: https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/upstream-virtio/

---

## Version History

**v0.1.1** (2025-01-18)
- âœ“ Added Looking Glass B7 installation
- âœ“ Integrated upstream VirtIO ISO with IVSHMEM driver
- âœ“ Created looking-glass-start helper script
- âœ“ Enhanced create-win11-vm with Looking Glass instructions
- âœ“ Added IVSHMEM device configuration
- âœ“ Automated shared memory permissions setup

**v0.1.1** (Previous)
- Initial MiOS-Build release
- Basic QEMU/KVM setup
- Cockpit integration
- Standard virtio-win ISO

---

**Enjoy near-native gaming performance in your VMs! ðŸš€**

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

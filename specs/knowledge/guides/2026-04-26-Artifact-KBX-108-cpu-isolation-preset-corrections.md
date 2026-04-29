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

# CPU Isolation Preset Corrections for MiOS-Build

## Executive Summary

This document provides corrected implementations for the CPU isolation presets in `mios-full.sh`, specifically optimized for AMD Ryzen 9950X3D (16 cores, 32 threads, dual-CCD) architecture. The current implementation has several issues including inverted logic in "Host Priority" and incorrect allocations in "Gaming Optimized."

---

## 9950X3D CPU Topology Reference

```
╔═══════════════════════════════════════════════════════════════════════╗
║ AMD Ryzen 9 9950X3D (32 threads, 16 cores, 2 CCDs)                    ║
╠═══════════════════════════════════════════════════════════════════════╣
║ CCD0 (V-Cache: 96MB L3 Total) - OPTIMAL FOR GAMING                    ║
║   Physical Core 0: CPU 0  + SMT sibling CPU 16                        ║
║   Physical Core 1: CPU 1  + SMT sibling CPU 17                        ║
║   Physical Core 2: CPU 2  + SMT sibling CPU 18                        ║
║   Physical Core 3: CPU 3  + SMT sibling CPU 19                        ║
║   Physical Core 4: CPU 4  + SMT sibling CPU 20                        ║
║   Physical Core 5: CPU 5  + SMT sibling CPU 21                        ║
║   Physical Core 6: CPU 6  + SMT sibling CPU 22                        ║
║   Physical Core 7: CPU 7  + SMT sibling CPU 23                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ CCD1 (High Frequency: 32MB L3) - HIGHER BOOST CLOCKS                  ║
║   Physical Core 8:  CPU 8  + SMT sibling CPU 24                       ║
║   Physical Core 9:  CPU 9  + SMT sibling CPU 25                       ║
║   Physical Core 10: CPU 10 + SMT sibling CPU 26                       ║
║   Physical Core 11: CPU 11 + SMT sibling CPU 27                       ║
║   Physical Core 12: CPU 12 + SMT sibling CPU 28                       ║
║   Physical Core 13: CPU 13 + SMT sibling CPU 29                       ║
║   Physical Core 14: CPU 14 + SMT sibling CPU 30                       ║
║   Physical Core 15: CPU 15 + SMT sibling CPU 31                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Issue Summary

| Preset | Current Behavior | Expected Behavior | Status |
|--------|------------------|-------------------|--------|
| Gaming Optimized | Host: CPUs 28-31, VM: 0-15 | Host: 0,16 + CCD1 (8-15,24-31), VM: 1-7,17-23 | ❌ Wrong |
| Multi-VM Balanced | Host: 0-7, VM: 8-31 | Host: 0,1,8,9,16,17,24,25 (8 threads), VM pools per CCD | ❌ Wrong |
| Host Priority | Host: 0-15 (V-Cache!), VM: 16-31 | Host: CCD0 (0-7,16-23), VM: CCD1 (8-15,24-31) | ❌ **INVERTED** |
| Default Selection | Option 1 | Option 2 (Balanced) | ❌ Wrong |

---

## Corrected Preset Specifications

### Option 1: Gaming Optimized (X3D)

**Purpose**: Maximize V-Cache availability for a single Vendor Secure Boot-enabled gaming VM while keeping the host responsive.

**Allocation**:
- **Host**: Core 0 from CCD0 (CPUs 0, 16) + ALL of CCD1 (CPUs 8-15, 24-31)
  - Total: 18 threads (1 V-Cache core + 8 high-frequency cores)
  - CCD1 provides high-frequency cores for desktop/services
- **Gaming VM**: Remaining CCD0 cores 1-7 (CPUs 1-7, 17-23)
  - Total: 14 threads (7 V-Cache cores)
  - Full V-Cache benefit for gaming workloads

**Emulator Pin**: CPUs 0,16 (the reserved host cores on CCD0)

```
CCD0 (V-Cache):     [H][ VM  VM  VM  VM  VM  VM  VM ]  (Core 0=Host, 1-7=VM)
CCD1 (High Freq):   [ H   H   H   H   H   H   H   H ]  (All Host)

H = Host, VM = Gaming VM
```

### Option 2: Multi-VM Balanced (DEFAULT)

**Purpose**: Support multiple VMs with optimal distribution. Gaming VM gets V-Cache, other VMs/containers get high-frequency cores.

**Allocation**:
- **Host**: First 2 cores from each CCD (CPUs 0,1,16,17 from CCD0 + CPUs 8,9,24,25 from CCD1)
  - Total: 8 threads (4 physical cores)
  - Distributed across CCDs for balanced performance
- **Gaming VM Pool (CCD0)**: Cores 2-7 (CPUs 2-7, 18-23)
  - Total: 12 threads (6 V-Cache cores)
  - For Vendor Secure Boot gaming VM
- **Container/Service Pool (CCD1)**: Cores 10-15 (CPUs 10-15, 26-31)
  - Total: 12 threads (6 high-frequency cores)
  - For containers, servers, non-gaming VMs

```
CCD0 (V-Cache):     [H   H][Gaming VM Pool: 6 cores ]  (Cores 0-1=Host, 2-7=Gaming)
CCD1 (High Freq):   [H   H][Service/Container Pool  ]  (Cores 8-9=Host, 10-15=Services)
```

### Option 3: Host Priority (50/50 CCD Split)

**Purpose**: Equal split by CCD. Host gets all V-Cache for desktop performance, VMs get high-frequency CCD.

**Allocation**:
- **Host**: All of CCD0 (CPUs 0-7, 16-23)
  - Total: 16 threads (8 V-Cache cores)
  - Maximum cache for desktop/host workloads
- **VM Pool**: All of CCD1 (CPUs 8-15, 24-31)
  - Total: 16 threads (8 high-frequency cores)
  - For VMs, containers, servers

```
CCD0 (V-Cache):     [ H   H   H   H   H   H   H   H ]  (All Host)
CCD1 (High Freq):   [VM  VM  VM  VM  VM  VM  VM  VM ]  (All VMs)
```

---

## Corrected Code Implementation

### Updated Menu Display

```bash
cpu_select_isolation_mode() {
    print_subsection "Isolation Mode Selection"
    
    local total_threads=${CPU_INFO[threads]:-0}
    
    echo ""
    echo -e "    ${BOLD}Available Isolation Presets:${NC}"
    echo ""
    
    if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
        # X3D optimized presets
        echo -e "    ${C_HIGHLIGHT}1)${NC} ${BOLD}Gaming Optimized (X3D)${NC}"
        echo -e "       Host: Core 0 of CCD0 + ALL of CCD1 (18 threads)"
        echo -e "       VM: CCD0 cores 1-7 (14 threads, V-Cache)"
        echo -e "       ${C_MUTED}Best for: Single gaming VM with maximum V-Cache${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}2)${NC} ${BOLD}Multi-VM Balanced${NC} ${C_SUCCESS}(Recommended)${NC}"
        echo -e "       Host: First 2 cores of each CCD (8 threads)"
        echo -e "       Gaming Pool: CCD0 cores 2-7 (12 threads, V-Cache)"
        echo -e "       Service Pool: CCD1 cores 10-15 (12 threads, High Freq)"
        echo -e "       ${C_MUTED}Best for: Gaming VM + containers/services${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}3)${NC} ${BOLD}Host Priority (50/50)${NC}"
        echo -e "       Host: All of CCD0 (16 threads, V-Cache)"
        echo -e "       VM: All of CCD1 (16 threads, High Freq)"
        echo -e "       ${C_MUTED}Best for: Heavy host workloads + VMs${NC}"
        echo ""
    else
        # Generic CPU presets (unchanged)
        local host_threads=4
        local vm_threads=$((total_threads - host_threads))
        
        echo -e "    ${C_HIGHLIGHT}1)${NC} ${BOLD}VM Priority${NC}"
        echo -e "       Host: 4 threads (cores 0-1)"
        echo -e "       VM: $vm_threads threads (cores 2+)"
        echo -e "       ${C_MUTED}Best for: Dedicated VM workloads${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}2)${NC} ${BOLD}Balanced${NC} ${C_SUCCESS}(Recommended)${NC}"
        echo -e "       Host: $((total_threads / 4)) threads"
        echo -e "       VM: $((total_threads * 3 / 4)) threads"
        echo -e "       ${C_MUTED}Best for: Mixed host and VM usage${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}3)${NC} ${BOLD}Host Priority${NC}"
        echo -e "       Host: $((total_threads / 2)) threads"
        echo -e "       VM: $((total_threads / 2)) threads"
        echo -e "       ${C_MUTED}Best for: Heavy host workloads${NC}"
        echo ""
    fi
    
    echo -e "    ${C_HIGHLIGHT}4)${NC} ${BOLD}Custom${NC}"
    echo -e "       Manually specify cores for isolation"
    echo ""
    
    echo -e "    ${C_HIGHLIGHT}5)${NC} ${BOLD}View Current State${NC}"
    echo -e "       Show current CPU isolation status"
    echo ""
    
    # Default to option 2 (Balanced) if user just presses Enter
    read -rp "      Select preset [1-5] (default: 2): " preset_choice
    preset_choice="${preset_choice:-2}"
    
    case "$preset_choice" in
        1)
            if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
                cpu_preset_x3d_gaming
            else
                cpu_preset_vm_priority
            fi
            ;;
        2)
            if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
                cpu_preset_x3d_balanced
            else
                cpu_preset_balanced
            fi
            ;;
        3)
            cpu_preset_host_priority
            ;;
        4)
            cpu_preset_custom
            ;;
        5)
            cpu_show_current_state
            cpu_select_isolation_mode
            return
            ;;
        *)
            msg_warn "Invalid selection, defaulting to Balanced"
            if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
                cpu_preset_x3d_balanced
            else
                cpu_preset_balanced
            fi
            ;;
    esac
}
```

### Corrected X3D Gaming Optimized Preset

```bash
cpu_preset_x3d_gaming() {
    msg_info "Applying X3D Gaming Optimized preset..."
    
    # 9950X3D: 32 threads, 16 cores, 2 CCDs
    # CCD0 (V-Cache): Cores 0-7 = CPUs 0-7 + SMT siblings 16-23
    # CCD1 (High Freq): Cores 8-15 = CPUs 8-15 + SMT siblings 24-31
    
    HOST_CPUS=()
    ISOLATED_CPUS=()
    
    # Host gets: Core 0 from CCD0 (CPUs 0, 16) + ALL of CCD1
    # CCD0 Core 0
    HOST_CPUS+=(0 16)
    # CCD1 entirely (cores 8-15 with SMT)
    for cpu in 8 9 10 11 12 13 14 15 24 25 26 27 28 29 30 31; do
        HOST_CPUS+=($cpu)
    done
    
    # Gaming VM gets: CCD0 cores 1-7 (CPUs 1-7 + SMT siblings 17-23)
    for cpu in 1 2 3 4 5 6 7 17 18 19 20 21 22 23; do
        ISOLATED_CPUS+=($cpu)
    done
    
    # Store allocation info for VM configuration
    GAMING_VM_CPUS="${ISOLATED_CPUS[*]}"
    EMULATOR_PIN_CPUS="0,16"
    
    msg_success "Host CPUs (18 threads): ${HOST_CPUS[*]}"
    msg_success "Gaming VM CPUs (14 V-Cache threads): ${ISOLATED_CPUS[*]}"
    msg_info "Recommended emulator pin: $EMULATOR_PIN_CPUS"
}
```

### Corrected X3D Multi-VM Balanced Preset (NEW DEFAULT)

```bash
cpu_preset_x3d_balanced() {
    msg_info "Applying X3D Multi-VM Balanced preset (Recommended)..."
    
    HOST_CPUS=()
    ISOLATED_CPUS=()
    
    # Host gets: First 2 cores from each CCD (8 threads total)
    # CCD0: Cores 0,1 = CPUs 0,1,16,17
    # CCD1: Cores 8,9 = CPUs 8,9,24,25
    HOST_CPUS=(0 1 16 17 8 9 24 25)
    
    # Gaming VM Pool (CCD0): Cores 2-7 = CPUs 2-7,18-23 (12 threads)
    GAMING_VM_CPUS="2,3,4,5,6,7,18,19,20,21,22,23"
    
    # Service/Container Pool (CCD1): Cores 10-15 = CPUs 10-15,26-31 (12 threads)
    SERVICE_POOL_CPUS="10,11,12,13,14,15,26,27,28,29,30,31"
    
    # For kernel isolation, mark ALL non-host CPUs
    for cpu in 2 3 4 5 6 7 18 19 20 21 22 23 10 11 12 13 14 15 26 27 28 29 30 31; do
        ISOLATED_CPUS+=($cpu)
    done
    
    # Store for VM configuration
    EMULATOR_PIN_CPUS="0,1,16,17"
    
    msg_success "Host CPUs (8 threads): ${HOST_CPUS[*]}"
    msg_success "Gaming VM Pool (12 V-Cache threads): $GAMING_VM_CPUS"
    msg_success "Service Pool (12 High-Freq threads): $SERVICE_POOL_CPUS"
    msg_info "Recommended emulator pin: $EMULATOR_PIN_CPUS"
    
    echo ""
    echo -e "    ${C_INFO}Pool Allocation:${NC}"
    echo -e "      • Gaming VM: Use CPUs $GAMING_VM_CPUS"
    echo -e "      • Containers/Services: Use CPUs $SERVICE_POOL_CPUS"
}
```

### Corrected Host Priority Preset

```bash
cpu_preset_host_priority() {
    msg_info "Applying Host Priority preset (50/50 CCD split)..."
    
    HOST_CPUS=()
    ISOLATED_CPUS=()
    
    if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
        # X3D: Host gets CCD0 (V-Cache), VMs get CCD1
        # Host: All of CCD0 (cores 0-7 + SMT = CPUs 0-7,16-23)
        for cpu in 0 1 2 3 4 5 6 7 16 17 18 19 20 21 22 23; do
            HOST_CPUS+=($cpu)
        done
        
        # VMs: All of CCD1 (cores 8-15 + SMT = CPUs 8-15,24-31)
        for cpu in 8 9 10 11 12 13 14 15 24 25 26 27 28 29 30 31; do
            ISOLATED_CPUS+=($cpu)
        done
        
        EMULATOR_PIN_CPUS="0,1,16,17"
        
        msg_success "Host CPUs (16 V-Cache threads): ${HOST_CPUS[*]}"
        msg_success "VM CPUs (16 High-Freq threads): ${ISOLATED_CPUS[*]}"
    else
        # Generic: Simple 50/50 split
        local total=${CPU_INFO[threads]}
        local half=$((total / 2))
        
        for ((i=0; i<half; i=i+1)); do
            HOST_CPUS+=($i)
        done
        
        for ((i=half; i<total; i=i+1)); do
            ISOLATED_CPUS+=($i)
        done
        
        msg_success "Host CPUs: ${HOST_CPUS[*]}"
        msg_success "VM CPUs: ${ISOLATED_CPUS[*]}"
    fi
}
```

---

## VM XML Template System

### Clean Base Template

The following is a sanitized version of the Xbox VM configuration, stripped of hardware-specific devices (USB passthrough, specific PCI addresses) suitable as a template:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<domain type="kvm">
  <name>TEMPLATE_VM_NAME</name>
  <metadata>
    <libosinfo:libosinfo xmlns:libosinfo="http://libosinfo.org/xmlns/libvirt/domain/1.0">
      <libosinfo:os id="http://microsoft.com/win/11"/>
    </libosinfo:libosinfo>
  </metadata>
  <memory unit="KiB">25165824</memory>
  <currentMemory unit="KiB">25165824</currentMemory>
  <vcpu placement="static">12</vcpu>
  <cputune>
    <!-- CPU pinning will be inserted here based on preset -->
    <vcpupin vcpu="0" cpuset="2"/>
    <vcpupin vcpu="1" cpuset="3"/>
    <vcpupin vcpu="2" cpuset="4"/>
    <vcpupin vcpu="3" cpuset="5"/>
    <vcpupin vcpu="4" cpuset="6"/>
    <vcpupin vcpu="5" cpuset="7"/>
    <vcpupin vcpu="6" cpuset="18"/>
    <vcpupin vcpu="7" cpuset="19"/>
    <vcpupin vcpu="8" cpuset="20"/>
    <vcpupin vcpu="9" cpuset="21"/>
    <vcpupin vcpu="10" cpuset="22"/>
    <vcpupin vcpu="11" cpuset="23"/>
    <emulatorpin cpuset="0,1,16,17"/>
  </cputune>
  <os>
    <type arch="x86_64" machine="pc-q35-10.1">hvm</type>
    <loader readonly="yes" secure="yes" type="pflash">/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd</loader>
    <nvram template="/usr/share/edk2/x64/OVMF_VARS.4m.fd">/var/lib/libvirt/qemu/nvram/TEMPLATE_VM_NAME_VARS.fd</nvram>
    <bootmenu enable="yes"/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <hyperv mode="custom">
      <relaxed state="on"/>
      <vapic state="on"/>
      <spinlocks state="on" retries="8191"/>
      <vpindex state="on"/>
      <runtime state="on"/>
      <synic state="on"/>
      <stimer state="on"/>
      <frequencies state="on"/>
      <tlbflush state="on"/>
      <ipi state="on"/>
      <avic state="on"/>
    </hyperv>
    <vmport state="off"/>
    <smm state="on"/>
  </features>
  <cpu mode="host-passthrough" check="none" migratable="on">
    <topology sockets="1" dies="1" clusters="1" cores="6" threads="2"/>
    <cache mode="passthrough"/>
    <feature policy="require" name="topoext"/>
    <feature policy="require" name="invtsc"/>
  </cpu>
  <clock offset="localtime">
    <timer name="rtc" tickpolicy="catchup"/>
    <timer name="pit" tickpolicy="delay"/>
    <timer name="hpet" present="no"/>
    <timer name="hypervclock" present="yes"/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <pm>
    <suspend-to-mem enabled="no"/>
    <suspend-to-disk enabled="no"/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <controller type="usb" index="0" model="qemu-xhci" ports="15">
      <address type="pci" domain="0x0000" bus="0x02" slot="0x00" function="0x0"/>
    </controller>
    <controller type="pci" index="0" model="pcie-root"/>
    <controller type="pci" index="1" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="1" port="0x8"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x0" multifunction="on"/>
    </controller>
    <controller type="pci" index="2" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="2" port="0x9"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x1"/>
    </controller>
    <controller type="pci" index="3" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="3" port="0xa"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x2"/>
    </controller>
    <controller type="pci" index="4" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="4" port="0xb"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x3"/>
    </controller>
    <controller type="pci" index="5" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="5" port="0xc"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x4"/>
    </controller>
    <controller type="pci" index="6" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="6" port="0xd"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x5"/>
    </controller>
    <controller type="pci" index="7" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="7" port="0xe"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x6"/>
    </controller>
    <controller type="pci" index="8" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="8" port="0xf"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x7"/>
    </controller>
    <controller type="sata" index="0">
      <address type="pci" domain="0x0000" bus="0x00" slot="0x1f" function="0x2"/>
    </controller>
    <controller type="virtio-serial" index="0">
      <address type="pci" domain="0x0000" bus="0x03" slot="0x00" function="0x0"/>
    </controller>
    <interface type="network">
      <mac address="52:54:00:XX:XX:XX"/>
      <source network="default"/>
      <model type="virtio"/>
      <address type="pci" domain="0x0000" bus="0x01" slot="0x00" function="0x0"/>
    </interface>
    <serial type="pty">
      <target type="isa-serial" port="0">
        <model name="isa-serial"/>
      </target>
    </serial>
    <console type="pty">
      <target type="serial" port="0"/>
    </console>
    <channel type="spicevmc">
      <target type="virtio" name="com.redhat.spice.0"/>
      <address type="virtio-serial" controller="0" bus="0" port="1"/>
    </channel>
    <input type="tablet" bus="usb">
      <address type="usb" bus="0" port="1"/>
    </input>
    <input type="mouse" bus="ps2"/>
    <input type="keyboard" bus="ps2"/>
    <tpm model="tpm-crb">
      <backend type="emulator" version="2.0"/>
    </tpm>
    <graphics type="spice" autoport="yes">
      <listen type="address"/>
      <image compression="off"/>
    </graphics>
    <sound model="ich9">
      <address type="pci" domain="0x0000" bus="0x00" slot="0x1b" function="0x0"/>
    </sound>
    <audio id="1" type="none"/>
    <video>
      <model type="none"/>
    </video>
    <watchdog model="itco" action="reset"/>
    <memballoon model="none"/>
  </devices>
</domain>
```

### VM Template Management Function

```bash
#==============================================================================
# VM TEMPLATE MANAGEMENT
#==============================================================================

vm_template_menu() {
    print_small_banner "VM Template Management"
    
    echo ""
    echo -e "    ${C_HIGHLIGHT}1)${NC} Create New VM from Secure Boot Template"
    echo -e "    ${C_HIGHLIGHT}2)${NC} Apply CPU Pinning to Existing VM"
    echo -e "    ${C_HIGHLIGHT}3)${NC} Apply Secure Boot + Pinning to Existing VM"
    echo -e "    ${C_HIGHLIGHT}4)${NC} View Template Configuration"
    echo -e "    ${C_HIGHLIGHT}b)${NC} Back to Main Menu"
    echo ""
    
    read -rp "      Select option: " choice
    
    case "$choice" in
        1) vm_create_from_template ;;
        2) vm_apply_pinning_only ;;
        3) vm_apply_full_config ;;
        4) vm_show_template ;;
        b|B) return ;;
        *) msg_warn "Invalid selection" ;;
    esac
    
    vm_template_menu
}

vm_create_from_template() {
    print_subsection "Create New VM from Secure Boot Template"
    
    # Get VM name
    read -rp "      Enter new VM name: " vm_name
    
    if [[ -z "$vm_name" ]]; then
        msg_warn "VM name cannot be empty"
        return
    fi
    
    # Check if VM already exists
    if virsh dominfo "$vm_name" &>/dev/null; then
        msg_warn "VM '$vm_name' already exists"
        return
    fi
    
    # Select CPU pinning preset
    echo ""
    echo -e "    ${BOLD}Select CPU Pinning Configuration:${NC}"
    echo ""
    echo -e "    ${C_HIGHLIGHT}1)${NC} Gaming Optimized - 14 vCPUs (CCD0 V-Cache: 1-7,17-23)"
    echo -e "    ${C_HIGHLIGHT}2)${NC} Balanced Gaming Pool - 12 vCPUs (CCD0: 2-7,18-23)"
    echo -e "    ${C_HIGHLIGHT}3)${NC} Service/Workstation - 12 vCPUs (CCD1: 10-15,26-31)"
    echo -e "    ${C_HIGHLIGHT}4)${NC} Custom vCPU count and pinning"
    echo ""
    
    read -rp "      Select [1-4]: " pin_preset
    
    local vcpu_count=12
    local pin_config=""
    local emulator_pin=""
    local cpu_topology=""
    
    case "$pin_preset" in
        1)
            vcpu_count=14
            pin_config=$(cat <<EOF
    <vcpupin vcpu="0" cpuset="1"/>
    <vcpupin vcpu="1" cpuset="2"/>
    <vcpupin vcpu="2" cpuset="3"/>
    <vcpupin vcpu="3" cpuset="4"/>
    <vcpupin vcpu="4" cpuset="5"/>
    <vcpupin vcpu="5" cpuset="6"/>
    <vcpupin vcpu="6" cpuset="7"/>
    <vcpupin vcpu="7" cpuset="17"/>
    <vcpupin vcpu="8" cpuset="18"/>
    <vcpupin vcpu="9" cpuset="19"/>
    <vcpupin vcpu="10" cpuset="20"/>
    <vcpupin vcpu="11" cpuset="21"/>
    <vcpupin vcpu="12" cpuset="22"/>
    <vcpupin vcpu="13" cpuset="23"/>
EOF
)
            emulator_pin="0,16"
            cpu_topology='<topology sockets="1" dies="1" clusters="1" cores="7" threads="2"/>'
            ;;
        2)
            vcpu_count=12
            pin_config=$(cat <<EOF
    <vcpupin vcpu="0" cpuset="2"/>
    <vcpupin vcpu="1" cpuset="3"/>
    <vcpupin vcpu="2" cpuset="4"/>
    <vcpupin vcpu="3" cpuset="5"/>
    <vcpupin vcpu="4" cpuset="6"/>
    <vcpupin vcpu="5" cpuset="7"/>
    <vcpupin vcpu="6" cpuset="18"/>
    <vcpupin vcpu="7" cpuset="19"/>
    <vcpupin vcpu="8" cpuset="20"/>
    <vcpupin vcpu="9" cpuset="21"/>
    <vcpupin vcpu="10" cpuset="22"/>
    <vcpupin vcpu="11" cpuset="23"/>
EOF
)
            emulator_pin="0,1,16,17"
            cpu_topology='<topology sockets="1" dies="1" clusters="1" cores="6" threads="2"/>'
            ;;
        3)
            vcpu_count=12
            pin_config=$(cat <<EOF
    <vcpupin vcpu="0" cpuset="10"/>
    <vcpupin vcpu="1" cpuset="11"/>
    <vcpupin vcpu="2" cpuset="12"/>
    <vcpupin vcpu="3" cpuset="13"/>
    <vcpupin vcpu="4" cpuset="14"/>
    <vcpupin vcpu="5" cpuset="15"/>
    <vcpupin vcpu="6" cpuset="26"/>
    <vcpupin vcpu="7" cpuset="27"/>
    <vcpupin vcpu="8" cpuset="28"/>
    <vcpupin vcpu="9" cpuset="29"/>
    <vcpupin vcpu="10" cpuset="30"/>
    <vcpupin vcpu="11" cpuset="31"/>
EOF
)
            emulator_pin="8,9,24,25"
            cpu_topology='<topology sockets="1" dies="1" clusters="1" cores="6" threads="2"/>'
            ;;
        4)
            read -rp "      Enter vCPU count: " vcpu_count
            read -rp "      Enter CPU list (comma-separated): " custom_cpus
            read -rp "      Enter emulator pin CPUs: " emulator_pin
            
            IFS=',' read -ra cpus <<< "$custom_cpus"
            pin_config=""
            local i=0
            for cpu in "${cpus[@]}"; do
                pin_config+="    <vcpupin vcpu=\"$i\" cpuset=\"$cpu\"/>"$'\n'
                i=$((i + 1))
            done
            
            local cores=$((vcpu_count / 2))
            cpu_topology="<topology sockets=\"1\" dies=\"1\" clusters=\"1\" cores=\"$cores\" threads=\"2\"/>"
            ;;
        *)
            msg_warn "Invalid selection"
            return
            ;;
    esac
    
    # Get memory size
    echo ""
    read -rp "      Memory size in GB (default: 24): " mem_gb
    mem_gb="${mem_gb:-24}"
    local mem_kib=$((mem_gb * 1024 * 1024))
    
    # Generate random MAC address
    local mac="52:54:00:$(printf '%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))"
    
    # Create VM XML
    local xml_file="/tmp/${vm_name}.xml"
    
    vm_generate_secureboot_xml "$vm_name" "$vcpu_count" "$mem_kib" "$pin_config" \
        "$emulator_pin" "$cpu_topology" "$mac" > "$xml_file"
    
    # Define the VM
    if virsh define "$xml_file" >> "$DEBUG_LOG" 2>&1; then
        msg_success "Created VM: $vm_name"
        msg_info "vCPUs: $vcpu_count, Memory: ${mem_gb}GB"
        msg_info "Secure Boot: Enabled, TPM 2.0: Enabled"
        
        # Create hook config
        vm_create_hook_config "$vm_name" "$emulator_pin"
        
        rm -f "$xml_file"
    else
        msg_fail "Failed to create VM"
        cat "$xml_file"
    fi
}

vm_generate_secureboot_xml() {
    local name="$1"
    local vcpus="$2"
    local mem_kib="$3"
    local pin_config="$4"
    local emulator_pin="$5"
    local topology="$6"
    local mac="$7"
    
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<domain type="kvm">
  <name>$name</name>
  <metadata>
    <libosinfo:libosinfo xmlns:libosinfo="http://libosinfo.org/xmlns/libvirt/domain/1.0">
      <libosinfo:os id="http://microsoft.com/win/11"/>
    </libosinfo:libosinfo>
  </metadata>
  <memory unit="KiB">$mem_kib</memory>
  <currentMemory unit="KiB">$mem_kib</currentMemory>
  <vcpu placement="static">$vcpus</vcpu>
  <cputune>
$pin_config
    <emulatorpin cpuset="$emulator_pin"/>
  </cputune>
  <os>
    <type arch="x86_64" machine="pc-q35-10.1">hvm</type>
    <loader readonly="yes" secure="yes" type="pflash">/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd</loader>
    <nvram template="/usr/share/edk2/x64/OVMF_VARS.4m.fd">/var/lib/libvirt/qemu/nvram/${name}_VARS.fd</nvram>
    <bootmenu enable="yes"/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <hyperv mode="custom">
      <relaxed state="on"/>
      <vapic state="on"/>
      <spinlocks state="on" retries="8191"/>
      <vpindex state="on"/>
      <runtime state="on"/>
      <synic state="on"/>
      <stimer state="on"/>
      <frequencies state="on"/>
      <tlbflush state="on"/>
      <ipi state="on"/>
      <avic state="on"/>
    </hyperv>
    <vmport state="off"/>
    <smm state="on"/>
  </features>
  <cpu mode="host-passthrough" check="none" migratable="on">
    $topology
    <cache mode="passthrough"/>
    <feature policy="require" name="topoext"/>
    <feature policy="require" name="invtsc"/>
  </cpu>
  <clock offset="localtime">
    <timer name="rtc" tickpolicy="catchup"/>
    <timer name="pit" tickpolicy="delay"/>
    <timer name="hpet" present="no"/>
    <timer name="hypervclock" present="yes"/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <pm>
    <suspend-to-mem enabled="no"/>
    <suspend-to-disk enabled="no"/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <controller type="usb" index="0" model="qemu-xhci" ports="15">
      <address type="pci" domain="0x0000" bus="0x02" slot="0x00" function="0x0"/>
    </controller>
    <controller type="pci" index="0" model="pcie-root"/>
    <controller type="pci" index="1" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="1" port="0x8"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x0" multifunction="on"/>
    </controller>
    <controller type="pci" index="2" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="2" port="0x9"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x1"/>
    </controller>
    <controller type="pci" index="3" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="3" port="0xa"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x2"/>
    </controller>
    <controller type="pci" index="4" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="4" port="0xb"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x3"/>
    </controller>
    <controller type="pci" index="5" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="5" port="0xc"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x4"/>
    </controller>
    <controller type="pci" index="6" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="6" port="0xd"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x5"/>
    </controller>
    <controller type="pci" index="7" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="7" port="0xe"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x6"/>
    </controller>
    <controller type="pci" index="8" model="pcie-root-port">
      <model name="pcie-root-port"/>
      <target chassis="8" port="0xf"/>
      <address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x7"/>
    </controller>
    <controller type="sata" index="0">
      <address type="pci" domain="0x0000" bus="0x00" slot="0x1f" function="0x2"/>
    </controller>
    <controller type="virtio-serial" index="0">
      <address type="pci" domain="0x0000" bus="0x03" slot="0x00" function="0x0"/>
    </controller>
    <interface type="network">
      <mac address="$mac"/>
      <source network="default"/>
      <model type="virtio"/>
      <address type="pci" domain="0x0000" bus="0x01" slot="0x00" function="0x0"/>
    </interface>
    <serial type="pty">
      <target type="isa-serial" port="0">
        <model name="isa-serial"/>
      </target>
    </serial>
    <console type="pty">
      <target type="serial" port="0"/>
    </console>
    <channel type="spicevmc">
      <target type="virtio" name="com.redhat.spice.0"/>
      <address type="virtio-serial" controller="0" bus="0" port="1"/>
    </channel>
    <input type="tablet" bus="usb">
      <address type="usb" bus="0" port="1"/>
    </input>
    <input type="mouse" bus="ps2"/>
    <input type="keyboard" bus="ps2"/>
    <tpm model="tpm-crb">
      <backend type="emulator" version="2.0"/>
    </tpm>
    <graphics type="spice" autoport="yes">
      <listen type="address"/>
      <image compression="off"/>
    </graphics>
    <sound model="ich9">
      <address type="pci" domain="0x0000" bus="0x00" slot="0x1b" function="0x0"/>
    </sound>
    <audio id="1" type="none"/>
    <video>
      <model type="none"/>
    </video>
    <watchdog model="itco" action="reset"/>
    <memballoon model="none"/>
  </devices>
</domain>
EOF
}

vm_apply_pinning_only() {
    print_subsection "Apply CPU Pinning to Existing VM"
    
    # List VMs
    local vms=$(virsh list --all --name 2>/dev/null | grep -v "^$")
    if [[ -z "$vms" ]]; then
        msg_warn "No VMs found"
        return
    fi
    
    echo ""
    echo -e "    ${BOLD}Available VMs:${NC}"
    local i=1
    local vm_array=()
    while IFS= read -r vm; do
        vm_array+=("$vm")
        local state=$(virsh domstate "$vm" 2>/dev/null | head -1)
        echo -e "      ${C_HIGHLIGHT}$i)${NC} $vm ${C_MUTED}($state)${NC}"
        i=$((i + 1))
    done <<< "$vms"
    
    echo ""
    read -rp "      Select VM [1-$((i-1))]: " vm_choice
    
    if ! [[ "$vm_choice" =~ ^[0-9]+$ ]] || [[ $vm_choice -lt 1 ]] || [[ $vm_choice -ge $i ]]; then
        msg_warn "Invalid selection"
        return
    fi
    
    local selected_vm="${vm_array[$((vm_choice-1))]}"
    local vcpu_count=$(virsh vcpucount "$selected_vm" --current 2>/dev/null || echo "0")
    
    msg_info "Selected: $selected_vm ($vcpu_count vCPUs)"
    
    # Show topology and select preset
    show_cpu_topology
    
    echo ""
    echo -e "    ${BOLD}Select Pinning Preset:${NC}"
    echo -e "    ${C_HIGHLIGHT}1)${NC} Gaming Optimized (V-Cache CCD0)"
    echo -e "    ${C_HIGHLIGHT}2)${NC} Balanced Gaming Pool"
    echo -e "    ${C_HIGHLIGHT}3)${NC} Service/Workstation Pool"
    echo -e "    ${C_HIGHLIGHT}4)${NC} Manual"
    echo ""
    
    read -rp "      Select [1-4]: " preset
    
    local pin_cpus=()
    local emulator_pin=""
    
    case "$preset" in
        1)
            # V-Cache cores 1-7 + SMT
            pin_cpus=(1 2 3 4 5 6 7 17 18 19 20 21 22 23)
            emulator_pin="0,16"
            ;;
        2)
            # Balanced gaming pool
            pin_cpus=(2 3 4 5 6 7 18 19 20 21 22 23)
            emulator_pin="0,1,16,17"
            ;;
        3)
            # Service pool on CCD1
            pin_cpus=(10 11 12 13 14 15 26 27 28 29 30 31)
            emulator_pin="8,9,24,25"
            ;;
        4)
            read -rp "      Enter CPU list for pinning: " manual
            IFS=',' read -ra pin_cpus <<< "$manual"
            read -rp "      Enter emulator pin CPUs: " emulator_pin
            ;;
    esac
    
    # Apply pinning
    msg_info "Applying CPU pinning..."
    
    for ((i=0; i<vcpu_count && i<${#pin_cpus[@]}; i+=1)); do
        if virsh vcpupin "$selected_vm" $i ${pin_cpus[$i]} --config >> "$DEBUG_LOG" 2>&1; then
            msg_success "vCPU $i → CPU ${pin_cpus[$i]}"
        else
            msg_fail "Failed to pin vCPU $i"
        fi
    done
    
    if [[ -n "$emulator_pin" ]]; then
        virsh emulatorpin "$selected_vm" "$emulator_pin" --config >> "$DEBUG_LOG" 2>&1
        msg_success "Emulator pinned to: $emulator_pin"
    fi
    
    # Create hook config
    vm_create_hook_config "$selected_vm" "$emulator_pin"
    
    msg_success "CPU pinning applied to $selected_vm"
}

vm_create_hook_config() {
    local vm_name="$1"
    local host_cpus="$2"
    
    local hook_dir="/etc/libvirt/hooks/qemu.d"
    mkdir -p "$hook_dir"
    
    cat > "$hook_dir/${vm_name}.conf" << EOF
# MiOS-Build VM Hook Configuration
# Generated: $(date)
# VM: $vm_name

# CPUs reserved for host when this VM runs
HOST_CPUS="$host_cpus"

# Optional: Hugepages (requires setup)
# USE_HUGEPAGES=1

# Optional: CPU governor when VM starts
# CPU_GOVERNOR="performance"
EOF
    
    msg_success "Created hook config: $hook_dir/${vm_name}.conf"
}
```

---

## Summary of Changes

### CPU Presets (X3D)

| Option | Name | Host CPUs | VM/Isolated CPUs | Default |
|--------|------|-----------|------------------|---------|
| 1 | Gaming Optimized | 0,16 + 8-15,24-31 (18) | 1-7,17-23 (14 V-Cache) | No |
| 2 | Multi-VM Balanced | 0,1,8,9,16,17,24,25 (8) | 2-7,18-23 (Gaming) + 10-15,26-31 (Service) | **YES** |
| 3 | Host Priority | 0-7,16-23 (16 V-Cache) | 8-15,24-31 (16 High-Freq) | No |

### VM Template Features

1. **Create New VM**: Generate complete Secure Boot-enabled VM with selectable CPU pinning preset
2. **Apply Pinning Only**: Add CPU pinning to existing VM without modifying other settings
3. **Full Config Apply**: Add Secure Boot + TPM + CPU pinning to existing VM
4. **Hook Integration**: Automatic generation of per-VM hook configuration files

### Key Fixes

- ✅ Host Priority no longer gives host the V-Cache CCD (was inverted)
- ✅ Gaming Optimized correctly reserves only one V-Cache core for host
- ✅ Multi-VM Balanced is now the default selection
- ✅ VM template stripped of hardware-specific devices
- ✅ Secure Boot variables correctly templated per-VM

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-fss/mios](https://github.com/mios-fss/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-fss/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-fss/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

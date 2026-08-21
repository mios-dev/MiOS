<!-- AI-hint: Chapter 22: CPU Topology and Performance Pinning. Maps CPU pinning allocations for isolated workloads. Details memory node alignment for reduced guest latencies. Covers scheduling priority and emulatorpin adjustments. -->

# Chapter 22: CPU Topology and Performance Pinning

> Part V: Deep Security, Cryptography & Hardware of the [MiOS manual](../manual.md).

This chapter covers the documentation for **CPU Topology and Performance Pinning** under MiOS.

### <a name="22_thread_allocation_strategies"></a>22.Thread Allocation Strategies: Thread Allocation Strategies

> Path Reference: `/usr/share/doc/mios/manual.md#22_thread_allocation_strategies`

#### Overview

CPU pinning partitions processing cores between virtual machines and the host.

## Policies
- **P-cores**: Assigned to virtual guest tasks.
- **E-cores**: Bound to host tasks and background AI lanes.
- **Automation**: Executed dynamically by [vm-cpu-pin-manager.sh](tools/vm-cpu-pin-manager.sh).

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="22_numa_node_awareness"></a>22.NUMA Node Awareness: NUMA Node Awareness

> Path Reference: `/usr/share/doc/mios/manual.md#22_numa_node_awareness`

#### Overview

NUMA alignment optimizes memory access times by keeping tasks close to memory nodes.

## Tuning
- **Alignment**: Virtual CPUs are pinned to matching physical RAM nodes.
- **Benefits**: Reduces cross-node latency and increases frame rates.
- **Controls**: Configured inside libvirt templates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="22_low_latency_vm_tuning"></a>22.Low-Latency VM Tuning: Low-Latency VM Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#22_low_latency_vm_tuning`

#### Overview

Tuning settings reduce virtualization scheduling latencies.

## Settings
- **Scheduling**: Prioritizes VM processes using real-time schedulers.
- **Emulator Pinning**: Isolates emulator tasks from primary worker threads.
- **Configurations**: Settings are managed in VM XML configurations.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

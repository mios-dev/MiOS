<!-- AI-hint: Specifies the 16-byte binary wire protocol, dual-tier Wasm/container sandboxing, and hierarchical work-stealing for mios-node. -->
<!-- AI-related: usr/lib/systemd/system/mios-node.service, usr/share/mios/mios.toml [blade.mesh], [nodes], [nodes.limits] -->
---
adr: 0020
title: "Edge micro-mesh 16-byte binary wire protocol, dual-tier sandboxing, and hierarchical work-stealing"
status: accepted
date: 2026-08-25
deciders: [operator, ai-pair]
tags: [mesh, node, binary-protocol, wasm, sandboxing, work-stealing, crdt]
laws: [2, 5, 7, 8, 12]
ssot_keys: [blade.mesh, nodes, nodes.limits, nodes.hardware_allowlist]
related_ws: [WS-NODE, WS-LANG, WS-BLADE]
supersedes: []
superseded_by: []
---

# ADR-0020: Edge micro-mesh 16-byte binary wire protocol, dual-tier sandboxing, and hierarchical work-stealing

## Status

**Accepted.** Establishes the native binary communication standard, security isolation tiers, and distributed task routing for edge `mios-node` blades.

## Context

Distributed MiOS edge clusters encompass heterogeneous nodes ranging from low-power single-board ARM computers to multi-GPU workstations. Inter-node coordination requires minimal protocol overhead, strong cryptographic isolation for delegated execution, and dynamic load balancing across volatile LAN and WAN connections.

## Decision

### 1. Fixed 16-Byte Binary Framing
All inter-node traffic uses a compact 16-byte binary header:
```
+----------------+----------------+----------------+----------------+
| Magic (2B)     | Opcode (1B)    | Flags (1B)     | Node ID (4B)   |
| 0x4D 0x49      | Type           | Bitmask        | Source ID      |
+----------------+----------------+----------------+----------------+
| Payload Length (4B)             | CRC32 Checksum (4B)             |
+---------------------------------+---------------------------------+
```
* End-to-end payload encryption uses X25519 key exchange and ChaCha20-Poly1305 authenticated symmetric ciphers.

### 2. Dual-Tier Sandboxing Model
* **Tier-1 Sandboxed Wasm (`wasmtime`)**: Fuel-bounded WebAssembly runtime for fast, lightweight telemetry, filtering, and sensor I/O tasks with zero host filesystem access.
* **Tier-2 Rootless Containers (Podman)**: Isolated cgroup namespaces with Ed25519 cryptographic image signature verification for complex compilation and tool execution workloads.

### 3. Hierarchical Latency-Aware Work-Stealing
Task offloading follows a strict hierarchy:
1. **Localhost Execution**: Evaluated first if local queue wait time is $<500	ext{ms}$.
2. **Adjacent LAN Peer Offload**: Broadcast over the 16-byte binary wire protocol ($<5	ext{ms}$) to idle LAN blades.
3. **WAN / Tailscale Coordinator Fallback**: Compressed payload delegation to remote central coordinator when local LAN capacity is fully exhausted.

### 4. CRDT Distributed State Reconciliation
Mesh state uses LWW-Element-Set and Vector Clock CRDTs for seamless multi-master divergence during network partitions, reconciling automatically upon link restoration.

## Rationale

A binary wire protocol paired with dual-tier sandboxing allows low-latency edge mesh task offloading while ensuring cryptographically verified execution isolation.

## Consequences

- Zero-serialization wire overhead provides ultra-low latency mesh coordination.
- Untrusted edge compute tasks run inside cryptographically verified, resource-bounded sandboxes.

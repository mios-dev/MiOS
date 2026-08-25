<!-- AI-hint: Chapter 65: Edge Micro-Mesh 16-Byte Wire Protocol, Dual-Tier Sandboxing & Hierarchical Work-Stealing. -->
# <a name="65_edge_micro_mesh_binary_wire_protocol_and_sandboxing"></a>Chapter 65: Edge Micro-Mesh 16-Byte Wire Protocol, Dual-Tier Sandboxing & Hierarchical Work-Stealing

> Part V: Federation & Edge Mesh of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#65_edge_micro_mesh_binary_wire_protocol_and_sandboxing`

#### Overview

Distributed MiOS edge meshes (`mios-node` / `WS-NODE` / ADR-0020) unite heterogeneous physical hardware—from embedded single-board ARM computers to multi-GPU workstations—into a unified collective computing fabric.

#### <a name="65_binary_wire_protocol"></a>65.1 The Fixed 16-Byte Binary Framing

To eliminate HTTP/JSON serialization overhead across low-bandwidth edge links, `mios-node` communicates over a compact 16-byte binary frame:

```
0                   1                   2                   3
0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Magic (0x4D 0x49)       |  Opcode (1B)  |   Flags (1B)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Node ID (4B)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Payload Length (4B)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        CRC32 Checksum (4B)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Payload Data (N Bytes...)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Payloads are end-to-end encrypted using X25519 key exchange authenticated with Ed25519 node identities and ChaCha20-Poly1305 symmetric ciphers.

#### <a name="65_dual_tier_sandboxing"></a>65.2 Dual-Tier Sandboxing Model

1. **Tier-1 Sandboxed Wasm (`wasmtime`)**: Fuel-bounded WebAssembly runtime executing sensor I/O, telemetry transforms, and local filter rules with zero host filesystem access.
2. **Tier-2 Rootless Podman Containers**: Isolated cgroup v2 namespaces with CPU core pinning, memory limits, and Ed25519 container image signature validation for complex compilation jobs.

#### <a name="65_hierarchical_work_stealing"></a>65.3 Hierarchical Latency-Aware Work-Stealing

Task placement resolves across a multi-tier hierarchy:
1. **Localhost Execution**: Handled on-device if queue latency is $<500	ext{ms}$.
2. **Adjacent LAN Peer Offload**: Broadcast over the 16-byte binary wire ($<5	ext{ms}$) to idle LAN blades.
3. **WAN / Tailscale Coordinator**: Delegated to remote coordinator over Tailscale/WireGuard overlay tunnels when local cluster capacity is saturated.

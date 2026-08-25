<!-- AI-hint: Chapter 70: Upstream Ecosystem Registry, Upstream Adoption Playbook & FOSS Drift Auditing. -->
# <a name="70_upstream_technology_registry_and_ecosystem_advances"></a>Chapter 70: Upstream Ecosystem Registry, Upstream Adoption Playbook & FOSS Drift Auditing

> Part VI: Upstream Ecosystem & Maintenance of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#70_upstream_technology_registry_and_ecosystem_advances`

#### Overview

MiOS builds directly on best-of-breed open source software, maintaining strict upstream parity and zero vendor lock-in.

#### <a name="70_upstream_registry"></a>70.1 Core Upstream Technology Mapping

| Layer | Upstream Project | Canonical Role in MiOS |
|---|---|---|
| **OS Substrate** | Fedora Project / `bootc` | Immutable OCI container base operating system |
| **Integrity** | `composefs` / `fs-verity` | Cryptographically sealed read-only `/usr` filesystem |
| **Inference Engine** | `llama.cpp` / `llama-swap` | Multi-model auto-swapping and KV cache paging |
| **Heavy GPU Lane** | `vLLM` / `SGLang` | High-throughput tensor-parallel GPU inference |
| **Datastore** | PostgreSQL + `pgvector` | Unified memory, vector recall, and event bus |
| **Virtualization** | KVM / QEMU / `libvirt` | VFIO discrete hardware passthrough |
| **Display Transport** | Looking Glass B6 | Inter-VM shared memory framebuffer |
| **Cluster & Storage** | `k3s` / CephFS | Single-node cluster fabric and distributed storage |

#### <a name="70_drift_auditing"></a>70.2 Upstream Drift Auditing & Playbook

Automated CI drift audits (`automation/98-drift-checks.sh`) continuously verify that local package pins, container digests, and API contracts remain synchronized with latest upstream releases without hand-pinned version decay.

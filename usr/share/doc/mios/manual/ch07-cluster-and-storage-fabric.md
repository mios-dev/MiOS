<!-- AI-hint: Chapter 07: Cluster and Storage Fabric. Outlines the mechanisms for expanding the workstation into a Kubernetes cluster. Explains CephFS containerized storage deployments and privileged exemptions. -->

# Chapter 07: Cluster and Storage Fabric

> Part II: The Agentic AI Stack of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Cluster and Storage Fabric** under MiOS.

### <a name="07_k3s_kubernetes_integration"></a>07.K3s Kubernetes Integration: K3s Kubernetes Integration

> Path Reference: `/usr/share/doc/mios/manual.md#07_k3s_kubernetes_integration`

#### Overview

MiOS workstation hosts can expand dynamically into single-node high-availability Kubernetes clusters.

- **Runtime daemon**: Managed via `mios-k3s.service` Quadlet.
- **Network Isolation**: Traefik acts as the ingress controller, managing routing protocols on standard cluster ports.
- **SELinux Policies**: Custom SELinux policies are applied by [37-k3s-selinux.sh](automation/37-k3s-selinux.sh) to ensure containerized cluster tasks do not violate host read-only security bounds.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 51** (Responses API): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L132)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="07_ceph_distributed_storage"></a>07.Ceph Distributed Storage: Ceph Distributed Storage

> Path Reference: `/usr/share/doc/mios/manual.md#07_ceph_distributed_storage`

#### Overview

Distributed storage clustering on MiOS is provisioned via containerized CephFS data planes and privileged exemptions.

- **Service quadlet**: Managed via `mios-ceph.service`.
- **Permissions**: Ceph requires low-level block device access, making it one of the few services exempt from Law 6 (running as host root).
- **User Integration**: User desktop directories (e.g. `~/Documents`) can be mapped directly onto local CephFS shares, enabling automated, encrypted background backups across the storage network.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 52** (Chat Completions): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L133)
- **Row 53** (Function calling / tools): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L134)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

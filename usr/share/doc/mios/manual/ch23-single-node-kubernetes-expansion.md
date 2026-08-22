<!-- AI-hint: Chapter 23: Single-Node Kubernetes Expansion. Covers resource boundaries between GNOME and K3s services. Details ingress routing rules in single-node clusters. Explains custom security policies allowing cluster containers. -->

# Chapter 23: Single-Node Kubernetes Expansion

> Part VI: Storage, Network & Web Planes of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Single-Node Kubernetes Expansion** under MiOS.

### <a name="23_k3s_workstation_coexistence"></a>23.K3s Workstation Coexistence: K3s Workstation Coexistence

> Path Reference: `/usr/share/doc/mios/manual.md#23_k3s_workstation_coexistence`

#### Overview

Integrating single-node K3s allows container orchestration without affecting GNOME resources.

## Operations
- **Isolation**: Runs K3s inside isolated runtime namespaces.
- **Gating**: Starts only when active profiles have cluster features enabled.
- **Limits**: Implements resource bounds to protect desktop tasks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="23_local_ingress_and_routing"></a>23.Local Ingress and Routing: Local Ingress and Routing

> Path Reference: `/usr/share/doc/mios/manual.md#23_local_ingress_and_routing`

#### Overview

Ingress configs manage external routing into local cluster services.

## Setup
- **Ingress**: Uses Traefik on port 6443.
- **Routing**: Routes local domains to active pods.
- **Ports**: Exposes services to the host network interface.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="23_k3s_selinux_policy_enforcement"></a>23.K3s SELinux Policy Enforcement: K3s SELinux Policy Enforcement

> Path Reference: `/usr/share/doc/mios/manual.md#23_k3s_selinux_policy_enforcement`

#### Overview

Custom SELinux rules protect the host from cluster workloads.

## Policies
- **Rules**: Applied by [19-k3s-selinux.sh](automation/19-k3s-selinux.sh).
- **Bounds**: Blocks cluster tasks from modifying read-only system files.
- **Validation**: Enforces SELinux policies at runtime.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

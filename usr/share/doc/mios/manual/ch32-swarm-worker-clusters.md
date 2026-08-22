<!-- AI-hint: Chapter 32: Swarm Worker Clusters. Covers dynamic worker provisioning via Quadlet templates. Details task partitioning and worker aggregation pipelines. Explains scheduling and routing algorithms across worker processes. -->

# Chapter 32: Swarm Worker Clusters

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Swarm Worker Clusters** under MiOS.

### <a name="32_swarm_node_provisioning"></a>32.Swarm Node Provisioning: Swarm Node Provisioning

> Path Reference: `/usr/share/doc/mios/manual.md#32_swarm_node_provisioning`

#### Overview

Adding swarm worker instances scales execution capacities dynamically.

## Steps
- **Template**: Uses `mios-llm-worker@.service` templates.
- **Target**: Spawns single-model processes on worker endpoints.
- **Discovery**: Automatically joins active host networks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="32_dynamic_fanout_orchestration"></a>32.Dynamic Fanout Orchestration: Dynamic Fanout Orchestration

> Path Reference: `/usr/share/doc/mios/manual.md#32_dynamic_fanout_orchestration`

#### Overview

The system splits complex queries and routes them to parallel workers.

## Pipeline
- **Fanout**: Tasks are split into independent components.
- **Routing**: Dynamic routing to active worker slots.
- **Synthesis**: Aggregates output files into a cohesive result.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="32_load_balancing_lanes"></a>32.Load Balancing Lanes: Load Balancing Lanes

> Path Reference: `/usr/share/doc/mios/manual.md#32_load_balancing_lanes`

#### Overview

Balances parallel model tasks based on health status metrics.

## Policies
- **Checking**: Probes worker load levels and memory limits.
- **Balancing**: Directs queries to the fastest available worker.
- **Failover**: Handles worker recovery on model load failures.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

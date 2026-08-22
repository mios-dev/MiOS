<!-- AI-hint: Chapter 11: Heavy GPU Lanes and SGLang/vLLM. Defines how SGLang is conditionally run depending on VRAM and workloads. Explains multi-model scaling and distributed worker configurations. Covers pre-allocation thresholds and dynamic offloading policies. -->

# Chapter 11: Heavy GPU Lanes and SGLang/vLLM

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Heavy GPU Lanes and SGLang/vLLM** under MiOS.

### <a name="11_sglang_gpu_gating_policies"></a>11.SGLang GPU Gating Policies: SGLang GPU Gating Policies

> Path Reference: `/usr/share/doc/mios/manual.md#11_sglang_gpu_gating_policies`

#### Overview

The alternate heavy lane utilizes SGLang (port key **`sglang`**) to serve large language models when hardware allows.

## Policies
- **VRAM Gating**: Checked at startup using `ConditionPathExists=/usr/share/mios/sglang/model/config.json`.
- **Exclusion**: SGLang and vLLM are mutually exclusive to prevent VRAM allocation conflicts.
- **Host Check**: Probes dGPU memory to verify available resources before launching SGLang containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="11_vllm_swarm_workers"></a>11.VLLM Swarm Workers: vLLM Swarm Workers

> Path Reference: `/usr/share/doc/mios/manual.md#11_vllm_swarm_workers`

#### Overview

The heavy lane uses vLLM (port key **`vllm`**) to run swarm worker instances.

## Operations
- **PagedAttention**: Uses vLLM's memory manager to scale batch concurrency.
- **Swarm worker**: Workers can be dynamically spun up using `mios-llm-worker@.service` templates.
- **Load Balancing**: Distributes token generation tasks across workers for high-volume jobs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="11_vram_allocation_and_scheduling"></a>11.VRAM Allocation and Scheduling: VRAM Allocation and Scheduling

> Path Reference: `/usr/share/doc/mios/manual.md#11_vram_allocation_and_scheduling`

#### Overview

VRAM scheduling isolates graphics memory resources between virtual machines (Looking Glass) and heavy reasoning lanes.

## Boundaries
- **VM Priority**: Virtual machines claim allocated VRAM statically at boot.
- **AI lane scaling**: Heavy LLM lanes adjust context sizes and batch bounds dynamically based on remaining VRAM.
- **Recovery**: Automatic shutdown of heavy lanes if a primary VM requests resources.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

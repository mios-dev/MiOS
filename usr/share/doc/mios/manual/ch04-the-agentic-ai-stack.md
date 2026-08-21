<!-- AI-hint: Chapter 04: The Agentic AI Stack. Describes the routing of all AI interactions through the MIOS_AI_ENDPOINT (Hermes gateway, port 8642). Details the primary front door on port 8640 used to route requests and fan out tasks. Outlines the operation of the tool-loop gateway and session manager running on port 8642. -->

# Chapter 04: The Agentic AI Stack

> Part II: The Agentic AI Stack of the [MiOS manual](../manual.md).

This chapter covers the documentation for **The Agentic AI Stack** under MiOS.

### <a name="04_unified_ai_endpoint"></a>04.Unified AI Endpoint: Unified AI Endpoint

> Path Reference: `/usr/share/doc/mios/manual.md#04_unified_ai_endpoint`

#### Overview

To avoid hardcoded vendor SDK dependencies, all intelligence pipelines on MiOS are routed through a single local endpoint on loopback named by `MIOS_AI_ENDPOINT` (the Hermes gateway on `:8642`). This endpoint abstractly translates chat-completions and embeddings requests to the active inference backend, ensuring client compatibility.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 29** (GHCR): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L87)
- **Row 30** (Sigstore / cosign): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L88)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_agent_pipe_orchestrator"></a>04.Agent Pipe Orchestrator: Agent Pipe Orchestrator

> Path Reference: `/usr/share/doc/mios/manual.md#04_agent_pipe_orchestrator`

#### Overview

The Agent Pipe Orchestrator (port **8640**) acts as the cognitive router for all user-facing interfaces.

When a prompt is submitted, the orchestrator performs intention refinement, decomposes the query into a task graph, coordinates sub-agents, executes tool loops, and streams aggregated answers back to client views.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 31** (syft): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L89)
- **Row 32** (shellcheck): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L90)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_mios_hermes_gateway"></a>04.MiOS Hermes Gateway: MiOS Hermes Gateway

> Path Reference: `/usr/share/doc/mios/manual.md#04_mios_hermes_gateway`

#### Overview

MiOS Hermes (port **8642**) is the core session and tool-loop execution manager.

- **Session Ownership**: Tracks state and history for active contexts.
- **Tool-Loop Execution**: Validates and executes tool calls sent by LLMs.
- **Skills Management**: Manages reusable python code blocks ("skills") loaded from system configurations.
- **Telemetry**: Exposes the Hermes Dashboard on port 9119 to monitor session states and tool logs.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 31** (syft): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L89)
- **Row 33** (hadolint): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L91)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_inference_lanes"></a>04.Inference Lanes: Inference Lanes

> Path Reference: `/usr/share/doc/mios/manual.md#04_inference_lanes`

#### Overview

MiOS splits LLM inference across separate functional lanes to match the host hardware resources:

1. **Light Lane (`mios-llm-light`)**: Running llama.cpp with a llama-swap proxy on port `11450` for everyday chat, code assistance, and embeddings.
2. **Heavy Lane (`mios-llm-heavy` / `mios-llm-heavy-alt`)**: Running SGLang (port `11441`) or vLLM (port `11440`) for large reasoning models, gated off by default.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 34** (openssl): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L92)
- **Row 35** (Podman Quadlet): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L98)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_unified_agent_memory"></a>04.Unified Agent Memory: Unified Agent Memory

> Path Reference: `/usr/share/doc/mios/manual.md#04_unified_agent_memory`

#### Overview

The persistent memory plane of MiOS is structured within a PostgreSQL database with the `pgvector` extension, running inside the `mios-pgvector` container (port 5432).

It stores raw session logs as episodic memory, and vector-embedded knowledge chunks as semantic memory. Dynamic cosine-similarity searches inject historical context directly into agent prompts.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 32** (shellcheck): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L90)
- **Row 36** (Container Device Interface (CDI)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L99)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

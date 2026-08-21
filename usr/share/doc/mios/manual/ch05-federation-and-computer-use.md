<!-- AI-hint: Chapter 05: Federation and Computer Use. Details the standardized MCP interface utilized by agents to discover external tools. Documents the A2A JSON-RPC specifications for peer delegation. Explains Wayland automation, vision grounding via UI-TARS, and pc-control tools. -->

# Chapter 05: Federation and Computer Use

> Part II: The Agentic AI Stack of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Federation and Computer Use** under MiOS.

### <a name="05_model_context_protocol"></a>05.Model Context Protocol: Model Context Protocol

> Path Reference: `/usr/share/doc/mios/manual.md#05_model_context_protocol`

#### Overview

The Model Context Protocol (MCP) defines the standard interface for how agents discover and execute system tools.

- **Registry**: Configured dynamically under `/usr/share/mios/ai/v1/mcp.json`.
- **Pre-installed Servers**: Includes `mios-fs` (filesystem), `mios-kb` (vector recall), and `mios-forge` (git repository control).
- **Confinement**: MCP servers execute tool scripts inside unprivileged namespaces.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 37** (containers.conf / storage.conf): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L100)
- **Row 38** (containers/storage): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L101)
- **Row 39** (containers/image): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L102)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="05_agent_to_agent_delegation"></a>05.Agent To Agent Delegation: Agent-to-Agent Delegation

> Path Reference: `/usr/share/doc/mios/manual.md#05_agent_to_agent_delegation`

#### Overview

Complex tasks are fanned out to specialized sub-agents using the Agent-to-Agent (A2A) protocol.

- **Communication**: Uses a JSON-RPC payload schema over standard loopback ports.
- **Discovery**: Agents query the registry at `/v1/agents` to discover capabilities.
- **Delegation**: The orchestrator delegates code tasks to the `mios-opencode` coding agent (port 8633), which modifies files and returns validation results.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 34** (openssl): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L92)
- **Row 37** (containers.conf / storage.conf): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L100)
- **Row 38** (containers/storage): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L101)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="05_vision_and_os_control"></a>05.Vision and OS Control: Vision and OS Control

> Path Reference: `/usr/share/doc/mios/manual.md#05_vision_and_os_control`

#### Overview

MiOS provides agents with the ability to interact directly with the GNOME desktop environment.

- **Vision Grounding**: Agents utilize the UI-TARS vision-language model to translate user requests into click coordinates on the Wayland display server.
- **Accessibility Tree**: Traversals are aided by the AT-SPI semantic screen tree, providing structural context for UI elements.
- **Execution**: Physical actions (mouse moves, clicks, keystrokes) are simulated using the custom `mios-pc-control` command suite.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 40** (nvidia-container-toolkit): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L103)
- **Row 41** (llama-swap): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L114)
- **Row 42** (Ollama): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L115)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

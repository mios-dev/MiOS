<!-- AI-hint: Chapter 13: Model Context Protocol Integration. Describes how to write custom Python or Go MCP servers. Covers how the AI gateway queries the system tool registry. Details how tools run in sandboxed namespaces to prevent host escapes. -->

# Chapter 13: Model Context Protocol Integration

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Model Context Protocol Integration** under MiOS.

### <a name="13_custom_mcp_server_design"></a>13.Custom MCP Server Design: Custom MCP Server Design

> Path Reference: `/usr/share/doc/mios/manual.md#13_custom_mcp_server_design`

#### Overview

Developers can extend agent capabilities by writing custom Model Context Protocol (MCP) servers.

## Guidelines
- **Language**: Python or Go is recommended.
- **Communication**: Uses JSON-RPC over stdin/stdout or SSE transport.
- **Registration**: Register the server in `/usr/share/mios/ai/v1/mcp.json` or `~/.config/mios/mcp.json`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="13_tool_discovery_protocols"></a>13.Tool Discovery Protocols: Tool Discovery Protocols

> Path Reference: `/usr/share/doc/mios/manual.md#13_tool_discovery_protocols`

#### Overview

The system uses dynamic tool discovery to collect active MCP tools at session start.

## Flow
1. **Parse Manifest**: Reads the registered MCP server list in `/v1/mcp`.
2. **Tool Handshake**: Connects to each server to fetch supported tools.
3. **API Mapping**: Maps tool capabilities to standard OpenAI-compatible function schemas.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="13_security_sandboxing_for_mcp"></a>13.Security Sandboxing for MCP: Security Sandboxing for MCP

> Path Reference: `/usr/share/doc/mios/manual.md#13_security_sandboxing_for_mcp`

#### Overview

To prevent malicious tool execution, MCP server processes are sandboxed.

## Sandboxing Details
- **Namespace Isolation**: Runs inside rootless container namespaces.
- **SELinux confinement**: Confinded using strict SELinux policies.
- **Filesystem Access**: Limited to designated sandbox directory spaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

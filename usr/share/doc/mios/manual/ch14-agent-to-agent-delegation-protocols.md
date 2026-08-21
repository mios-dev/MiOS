<!-- AI-hint: Chapter 14: Agent-to-Agent Delegation Protocols. Details the communications standard and payload schema for agent delegation. Explains how the coding subagent (MiOS-OpenCode) takes over code modification. Defines the capability-based security mapping across cooperative agents. -->

# Chapter 14: Agent-to-Agent Delegation Protocols

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Agent-to-Agent Delegation Protocols** under MiOS.

### <a name="14_json_rpc_delegation_specification"></a>14.JSON-RPC Delegation Spec: JSON-RPC Delegation Specification

> Path Reference: `/usr/share/doc/mios/manual.md#14_json_rpc_delegation_specification`

#### Overview

The Agent-to-Agent (A2A) protocol defines how agents delegate tasks to peer nodes.

## Payload Example
```json
{
  "jsonrpc": "2.0",
  "method": "delegate_task",
  "params": {
    "task": "Refactor install.sh line 42",
    "specialist": "mios-opencode"
  },
  "id": 1
}
```

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="14_opencode_specialist_handoffs"></a>14.OpenCode Specialist Handoffs: OpenCode Specialist Handoffs

> Path Reference: `/usr/share/doc/mios/manual.md#14_opencode_specialist_handoffs`

#### Overview

Coding tasks are fanned out to the `mios-opencode` coding specialist on the `opencode_gateway` port.

## Execution Flow
1. **Identify Task**: The orchestrator detects code modifications.
2. **RPC Handoff**: Delegates the file editing task to the coding agent.
3. **Execution**: The coding agent edits the target files.
4. **Verification**: Runs tests in the sandboxed container and returns the results.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="14_peer_to_peer_trust_models"></a>14.Peer-to-Peer Trust Models: Peer-to-Peer Trust Models

> Path Reference: `/usr/share/doc/mios/manual.md#14_peer_to_peer_trust_models`

#### Overview

A2A communications are secured through capability-based access controls.

## Details
- **Tokens**: Loopback calls are secured via dynamically rotated tokens.
- **Verification**: Agents verify peer signatures before executing tasks.
- **Audit Logs**: All delegated tasks are logged in the Postgres database.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

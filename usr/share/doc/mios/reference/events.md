<!-- AI-hint: Derived reference documentation for observability event schema kinds. -->

# MiOS Event Kinds

This document is derived directly from system event definitions and schema files.

<!-- MIOS-GEN:events -->
| Event Kind | Description |
|---|---|
| `agent` | agent | operator |
| `agent.memory_saved` | Emitted when an agent saves a fact to memory |
| `agent.tool_call` | Emitted when an agent invokes a tool verb |
| `assigned` | assigned | completed | stalled |
| `blade.role_applied` | Emitted when blade archetype role changes |
| `config.changed` | Emitted when mios.toml or runtime configuration changes |
| `global` | global | agent:<name> | conversation:<id> |
| `pending` | pending | approved | denied |
| `security.auth_posture` | Emitted when auth posture status changes |
| `service.failover` | Emitted when workload placement failover triggers |
| `user` | user | system | service |
| `warm` | warm | hot |

<!-- derived from event schema definitions (12 event(s)) -->
<!-- /MIOS-GEN:events -->

# Project: MiOS Roadmap Tasks Execution & CI Parity

## Architecture
MiOS is an immutable, bootc/OCI-shaped Fedora workstation that is also a local, self-replicating agentic AI operating system.
All runtime verbs and extensions follow strict Architectural Laws:
- Modular Libexec Layout: All new domain verbs reside under `usr/libexec/mios/<domain>/` to preserve the `max_libexec_verbs = 285/285` ceiling.
- Python/Rust Runtime Implementation: Implemented in Python standard library or compiled Rust to preserve `ps_lines = 22618/22618`.
- Hermetic Test Suites: Authored under `tests/test-*.py` using standard `unittest` and registered in `usr/share/mios/mios.toml` under `[ci.tiers] unit`.
- SSOT Synchronization & CI Parity: `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`, and 7 machine projections synced via `tools/sync-generated.sh`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | MCP-01 Sandbox | Bubblewrap namespace and filesystem isolation for external MCP tool servers | M1 | T-377 / AGY-1975 |
| 2 | SEC-06 HITL Approval | Interactive human-in-the-loop permission escalation prompts for destructive MCP tools | M2 | T-378 / AGY-1976 |
| 3 | GRAPH-01 Knowledge Traversal | Recursive CTE knowledge traversal across pgvector knowledge triples | M3 | T-379 / AGY-1977 |
| 4 | PROMPT-01 Context Pruning | Contextual prompt compression and selective linguistic token pruning (~25% savings) | M4 | T-380 / AGY-1978 |
| 5 | A2A-01 Attestation | Agent-to-Agent mutual capability exchange and Ed25519 cryptographic attestation | M5 | T-381 / AGY-1979 |
| 6 | CI Suites & SSOT Sync | Test suite registration in mios.toml, task parity updates, sync-generated, and 7 CI validation passes | M6 | R2, R3, R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1-MCP-Sandbox | Implement `usr/libexec/mios/mcp/sandbox.py` + `tests/test-mcp-sandbox.py` (T-377) | none | DONE |
| 2 | M2-SEC-Approval | Implement `usr/libexec/mios/sec/approval.py` + `tests/test-hitl-approval.py` (T-378) | M1 | DONE |
| 3 | M3-GRAPH-Traversal | Implement `usr/libexec/mios/graph/traversal.py` + `tests/test-knowledge-graph.py` (T-379) | M2 | DONE |
| 4 | M4-PROMPT-Pruning | Implement `usr/libexec/mios/prompt/pruning.py` + `tests/test-prompt-pruning.py` (T-380) | M3 | DONE |
| 5 | M5-A2A-Attestation | Implement `usr/libexec/mios/a2a/attestation.py` + `tests/test-a2a-attestation.py` (T-381) | M4 | DONE |
| 6 | M6-CI-Sync-Commit | Register tests in `mios.toml`, update `TASKS.md`, `AGY-TASKS.md`, run `roadmap-index.py`, `sync-generated.sh`, pass all 7 CI checks, commit and push | M1-M5 | DONE |

## Interface Contracts
### M1: MCP Sandbox ↔ Agent-Pipe
- `McpSandbox(server_name: str, allow_net: bool = False, custom_ro_binds: list[str] = None)`
- `build_command(inner_cmd: list[str]) -> list[str]`
- Wraps target execution with `bwrap --die-with-parent --new-session --unshare-all --ro-bind /usr /usr ...`

### M2: HITL Approval ↔ Tool Dispatch
- `ApprovalEngine(patterns: list[str] = None, ttl_seconds: int = 120)`
- `requires_approval(command: str) -> bool`
- `create_request(tool_name: str, command: str) -> ApprovalRequest`
- `approve(request_id: str, operator: str) -> str` (token)
- `validate_token(request_id: str, token: str) -> bool`

### M3: Knowledge Graph ↔ pgvector / CTE Traversal
- `KnowledgeGraph(db_uri: str = None)`
- `add_triple(subject: str, predicate: str, object_: str, properties: dict = None)`
- `get_recursive_dependencies(root: str, max_depth: int = 5) -> list[str]`
- `traverse(root: str, max_depth: int = 5) -> list[dict]`

### M4: Prompt Compressor ↔ Agent Pipeline
- `PromptPruner(min_ratio: float = 0.20)`
- `compress(text: str) -> tuple[str, dict]`
- Prunes redundant filler, boilerplate, duplicate headings while preserving code blocks and syntax verbatim.

### M5: A2A Authenticator ↔ Peer Nodes
- `A2AAuthenticator(node_id: int, private_key: bytes, public_key: bytes)`
- `create_card(agent_name: str, capabilities: list[str], ttl_seconds: int = 3600) -> dict`
- `verify_card(card: dict, trusted_public_key: bytes) -> bool`

## Code Layout
- `usr/libexec/mios/mcp/sandbox.py`: MCP bubblewrap namespace sandbox engine
- `usr/libexec/mios/sec/approval.py`: Interactive HITL approval and permission escalation engine
- `usr/libexec/mios/graph/traversal.py`: Recursive CTE knowledge graph traversal engine
- `usr/libexec/mios/prompt/pruning.py`: Contextual prompt compression and token pruning engine
- `usr/libexec/mios/a2a/attestation.py`: A2A cryptographic capability attestation engine
- `tests/test-mcp-sandbox.py`: Unit test suite for M1
- `tests/test-hitl-approval.py`: Unit test suite for M2
- `tests/test-knowledge-graph.py`: Unit test suite for M3
- `tests/test-prompt-pruning.py`: Unit test suite for M4
- `tests/test-a2a-attestation.py`: Unit test suite for M5
- `usr/share/mios/mios.toml`: SSOT registry containing `[ci.tiers] unit` test registrations
- `TASKS.md`, `AGY-TASKS.md`, `ROADMAP.md`: Project task registries

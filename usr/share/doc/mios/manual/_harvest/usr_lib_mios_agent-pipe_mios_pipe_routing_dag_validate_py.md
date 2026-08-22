<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Perform pre-execution validation and Kahn topological...

Perform pre-execution validation and Kahn topological classification over plan nodes.
    
    Checks for:
    1. Duplicate node IDs
    2. Self-loop dependencies
    3. Dangling dependencies (referencing non-existent node IDs)
    4. Cycles (via Kahn's algorithm)
    5. Orphan roots (graphs with nodes but no valid entry point)
    
    Returns a DAGValidationVerdict containing classification and a sanitized remediation order.

<!-- mios-src:623923225a95 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_validate.py:36-46 -->

# AI-hint: Pure pre-execution validator and Kahn topological classifier for runtime agent DAGs.
# AI-related: mios_pipe/routing/dag_exec.py, test_mios_dag_validate.py
"""Pure pre-execution DAG validator using Kahn topological classification."""

from __future__ import annotations

import collections
import dataclasses
from typing import Any, Dict, List, Set, Union


@dataclasses.dataclass
class DAGValidationVerdict:
    """Typed result of DAG pre-execution validation."""
    is_valid: bool
    status: str  # "acyclic" | "cycle_nodes" | "dangling_deps" | "duplicate_ids" | "orphan_roots"
    cycle_nodes: List[str] = dataclasses.field(default_factory=list)
    dangling_deps: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    duplicate_ids: List[str] = dataclasses.field(default_factory=list)
    topological_order: List[str] = dataclasses.field(default_factory=list)
    remediation_order: List[Dict[str, Any]] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "cycle_nodes": self.cycle_nodes,
            "dangling_deps": self.dangling_deps,
            "duplicate_ids": self.duplicate_ids,
            "topological_order": self.topological_order,
            "remediation_order_len": len(self.remediation_order),
        }


def validate_dag(dag_or_nodes: Union[Dict[str, Any], List[Dict[str, Any]]]) -> DAGValidationVerdict:
    """Perform pre-execution validation and Kahn topological classification over plan nodes.
    
    Checks for:
    1. Duplicate node IDs
    2. Self-loop dependencies
    3. Dangling dependencies (referencing non-existent node IDs)
    4. Cycles (via Kahn's algorithm)
    5. Orphan roots (graphs with nodes but no valid entry point)
    
    Returns a DAGValidationVerdict containing classification and a sanitized remediation order.
    """
    if isinstance(dag_or_nodes, dict):
        raw_nodes = dag_or_nodes.get("nodes") or []
    elif isinstance(dag_or_nodes, list):
        raw_nodes = dag_or_nodes
    else:
        raw_nodes = []

    nodes: List[Dict[str, Any]] = [n for n in raw_nodes if isinstance(n, dict) and "id" in n]

    if not nodes:
        return DAGValidationVerdict(
            is_valid=True,
            status="acyclic",
            topological_order=[],
            remediation_order=[],
        )

    # 1. Duplicate IDs
    seen_ids: Set[str] = set()
    dup_ids: Set[str] = set()
    unique_nodes: List[Dict[str, Any]] = []
    
    for n in nodes:
        nid = str(n["id"])
        if nid in seen_ids:
            dup_ids.add(nid)
        else:
            seen_ids.add(nid)
            unique_nodes.append(n)

    duplicate_list = sorted(list(dup_ids))

    # 2. Map nodes by ID
    by_id: Dict[str, Dict[str, Any]] = {str(n["id"]): n for n in unique_nodes}
    valid_ids: Set[str] = set(by_id.keys())

    # 3. Dangling deps & Self-loops
    dangling: Dict[str, List[str]] = {}
    clean_deps: Dict[str, Set[str]] = {}

    for nid, n in by_id.items():
        raw_deps = n.get("deps") or []
        n_dangling = []
        n_clean = set()
        for d in raw_deps:
            sd = str(d)
            if sd == nid:
                # Self-loop: invalid dependency
                pass
            elif sd not in valid_ids:
                n_dangling.append(sd)
            else:
                n_clean.add(sd)

        if n_dangling:
            dangling[nid] = n_dangling
        clean_deps[nid] = n_clean

    # Determine structural defects before Kahn
    if duplicate_list:
        remed_order = _build_linear_remediation(unique_nodes, clean_deps)
        return DAGValidationVerdict(
            is_valid=False,
            status="duplicate_ids",
            duplicate_ids=duplicate_list,
            dangling_deps=dangling,
            remediation_order=remed_order,
        )

    if dangling:
        remed_order = _build_linear_remediation(unique_nodes, clean_deps)
        return DAGValidationVerdict(
            is_valid=False,
            status="dangling_deps",
            dangling_deps=dangling,
            remediation_order=remed_order,
        )

    # 4. Kahn's Algorithm for Topological Sorting & Cycle Detection
    in_degree: Dict[str, int] = {nid: len(deps_set) for nid, deps_set in clean_deps.items()}
    adjacency: Dict[str, List[str]] = collections.defaultdict(list)
    for nid, deps_set in clean_deps.items():
        for d in deps_set:
            adjacency[d].append(nid)

    # Queue of nodes with in_degree == 0
    zero_in_degree = collections.deque([nid for nid in valid_ids if in_degree[nid] == 0])

    # Check for cycle / orphan roots when no root node exists
    if not zero_in_degree and valid_ids:
        remed_order = _build_linear_remediation(unique_nodes, clean_deps)
        return DAGValidationVerdict(
            is_valid=False,
            status="cycle_nodes",
            cycle_nodes=sorted(list(valid_ids)),
            remediation_order=remed_order,
        )

    topo_order: List[str] = []
    while zero_in_degree:
        curr = zero_in_degree.popleft()
        topo_order.append(curr)
        for neighbor in adjacency[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                zero_in_degree.append(neighbor)

    if len(topo_order) == len(valid_ids):
        # Check if any self-loops were filtered out
        has_self_loops = any(str(nid) in (n.get("deps") or []) for nid, n in by_id.items())
        if has_self_loops:
            self_loop_nodes = sorted([nid for nid, n in by_id.items() if str(nid) in (n.get("deps") or [])])
            remed_order = _build_linear_remediation(unique_nodes, clean_deps)
            return DAGValidationVerdict(
                is_valid=False,
                status="cycle_nodes",
                cycle_nodes=self_loop_nodes,
                topological_order=topo_order,
                remediation_order=remed_order,
            )

        # Acyclic and fully valid!
        remed_order = [by_id[nid] for nid in topo_order]
        return DAGValidationVerdict(
            is_valid=True,
            status="acyclic",
            topological_order=topo_order,
            remediation_order=remed_order,
        )

    # Cycle detected
    cycle_node_ids = sorted([nid for nid in valid_ids if nid not in set(topo_order)])
    remed_order = _build_linear_remediation(unique_nodes, clean_deps)

    return DAGValidationVerdict(
        is_valid=False,
        status="cycle_nodes",
        cycle_nodes=cycle_node_ids,
        topological_order=topo_order,
        remediation_order=remed_order,
    )


def _build_linear_remediation(nodes: List[Dict[str, Any]], clean_deps: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
    """Build a deterministic single-agent / linearized order for remediation.
    Strips invalid/dangling/cyclic dependencies so nodes can execute sequentially."""
    sanitized: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for n in nodes:
        nid = str(n["id"])
        if nid in seen:
            continue
        seen.add(nid)
        n_copy = dict(n)
        # Strip deps to valid previous nodes in linear order
        valid_prev = clean_deps.get(nid, set()) & (seen - {nid})
        n_copy["deps"] = sorted(list(valid_prev))
        sanitized.append(n_copy)

    return sanitized

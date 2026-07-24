# AI-hint: Unit test suite for pre-execution DAG validator dag_validate.py.
# AI-related: mios_pipe/routing/dag_validate.py
"""Unit tests for mios_pipe.routing.dag_validate."""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.routing.dag_validate import validate_dag, DAGValidationVerdict


class TestDAGValidate(unittest.TestCase):
    """Test Kahn topological classification and validation over plan nodes."""

    def test_valid_acyclic_dag(self):
        dag = {
            "nodes": [
                {"id": "1", "tool": "search", "deps": []},
                {"id": "2", "tool": "read", "deps": ["1"]},
                {"id": "3", "tool": "summarize", "deps": ["1", "2"]},
            ]
        }
        verdict = validate_dag(dag)
        self.assertTrue(verdict.is_valid)
        self.assertEqual(verdict.status, "acyclic")
        self.assertEqual(verdict.topological_order, ["1", "2", "3"])
        self.assertEqual(len(verdict.remediation_order), 3)

    def test_cycle_detection(self):
        dag = {
            "nodes": [
                {"id": "1", "tool": "node1", "deps": ["2"]},
                {"id": "2", "tool": "node2", "deps": ["1"]},
            ]
        }
        verdict = validate_dag(dag)
        self.assertFalse(verdict.is_valid)
        self.assertEqual(verdict.status, "cycle_nodes")
        self.assertEqual(sorted(verdict.cycle_nodes), ["1", "2"])
        self.assertEqual(len(verdict.remediation_order), 2)

    def test_self_loop_detection(self):
        dag = {
            "nodes": [
                {"id": "1", "tool": "self_loop", "deps": ["1"]},
            ]
        }
        verdict = validate_dag(dag)
        self.assertFalse(verdict.is_valid)
        self.assertEqual(verdict.status, "cycle_nodes")
        self.assertIn("1", verdict.cycle_nodes)
        self.assertEqual(len(verdict.remediation_order), 1)

    def test_dangling_dependency(self):
        dag = {
            "nodes": [
                {"id": "1", "tool": "node1", "deps": ["999"]},
            ]
        }
        verdict = validate_dag(dag)
        self.assertFalse(verdict.is_valid)
        self.assertEqual(verdict.status, "dangling_deps")
        self.assertIn("1", verdict.dangling_deps)
        self.assertEqual(verdict.dangling_deps["1"], ["999"])
        self.assertEqual(len(verdict.remediation_order), 1)

    def test_duplicate_node_ids(self):
        dag = {
            "nodes": [
                {"id": "1", "tool": "node1_first", "deps": []},
                {"id": "1", "tool": "node1_duplicate", "deps": []},
            ]
        }
        verdict = validate_dag(dag)
        self.assertFalse(verdict.is_valid)
        self.assertEqual(verdict.status, "duplicate_ids")
        self.assertIn("1", verdict.duplicate_ids)
        self.assertEqual(len(verdict.remediation_order), 1)

    def test_orphan_roots(self):
        # Closed cycle graph with no root node (all in_degree > 0)
        nodes = [
            {"id": "a", "deps": ["b"]},
            {"id": "b", "deps": ["c"]},
            {"id": "c", "deps": ["a"]},
        ]
        verdict = validate_dag(nodes)
        self.assertFalse(verdict.is_valid)
        self.assertIn(verdict.status, ("orphan_roots", "cycle_nodes"))
        self.assertEqual(len(verdict.remediation_order), 3)


if __name__ == "__main__":
    unittest.main()

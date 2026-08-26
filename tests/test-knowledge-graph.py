#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-RAG / GRAPH-01 recursive CTE knowledge traversal.
# AI-related: usr/libexec/mios/graph/traversal.py, usr/share/mios/postgres/schema-init.sql
"""
Automated unit tests for MiOS Knowledge Graph Triple Storage & Recursive CTE Traversal Engine.
Validates triple ingestion, direct dependencies, multi-hop walks, reverse traversal,
cycle detection, depth bounds, properties, embeddings, SQL generation, and CLI interface.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TRAVERSAL_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "graph", "traversal.py")

spec = importlib.util.spec_from_file_location("traversal", _TRAVERSAL_PATH)
if spec and spec.loader:
    traversal = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = traversal
    spec.loader.exec_module(traversal)
else:
    raise ImportError(f"Could not load traversal module from {_TRAVERSAL_PATH}")


class TestKnowledgeGraphTraversal(unittest.TestCase):
    """Validates in-memory graph operations, recursive dependency querying, cycle handling, and metadata."""

    def setUp(self) -> None:
        """Set up in-memory KnowledgeGraph populated with a standard topology."""
        self.graph = traversal.KnowledgeGraph()
        # Seed standard MiOS service dependency chain:
        # agent-pipe -> hermes -> mios-llm-light -> llama-swap -> llama.cpp
        # agent-pipe -> pgvector
        # mios-llm-light -> nomic-embed-text
        self.graph.add_triple("agent-pipe", "routes_to", "hermes", {"port": 8642})
        self.graph.add_triple("agent-pipe", "stores_in", "pgvector", {"port": 5432})
        self.graph.add_triple("hermes", "delegates_to", "mios-llm-light", {"port": 11450})
        self.graph.add_triple("mios-llm-light", "depends_on", "llama-swap")
        self.graph.add_triple("llama-swap", "depends_on", "llama.cpp")
        self.graph.add_triple(
            "mios-llm-light",
            "serves",
            "nomic-embed-text",
            {"dim": 768},
            [0.1, 0.2, 0.3],
        )

    def tearDown(self) -> None:
        """Clean up graph resources."""
        self.graph.close()

    def test_single_triple_ingestion(self) -> None:
        """Validates adding a single triple returns a positive row ID."""
        row_id = self.graph.add_triple(
            subject="owui",
            predicate="connects_to",
            object_="agent-pipe",
            properties={"auth": "bearer"},
            embedding=[0.05, 0.12, 0.88],
        )
        self.assertIsInstance(row_id, int)
        self.assertGreater(row_id, 0)
        deps = self.graph.get_dependencies("owui")
        self.assertEqual(deps, ["agent-pipe"])

    def test_batch_triple_ingestion(self) -> None:
        """Validates batch adding triples with varying tuple schemas."""
        batch = [
            ("searxng", "backs", "owui"),
            ("searxng", "listens_on", "port_8888", {"proto": "http"}),
            ("guacamole", "manages", "browser_desktop", {"auth": "psql"}, [0.1, 0.9]),
        ]
        inserted = self.graph.add_triples(batch)
        self.assertEqual(inserted, 3)
        self.assertIn("owui", self.graph.get_dependencies("searxng"))
        self.assertIn("port_8888", self.graph.get_dependencies("searxng"))
        self.assertIn("browser_desktop", self.graph.get_dependencies("guacamole"))

    def test_direct_dependency_lookup(self) -> None:
        """Validates 1-hop direct dependency queries."""
        deps = self.graph.get_dependencies("agent-pipe")
        self.assertEqual(len(deps), 2)
        self.assertIn("hermes", deps)
        self.assertIn("pgvector", deps)

        # Predicate filtering
        routes = self.graph.get_dependencies("agent-pipe", predicate="routes_to")
        self.assertEqual(routes, ["hermes"])
        stores = self.graph.get_dependencies("agent-pipe", predicate="stores_in")
        self.assertEqual(stores, ["pgvector"])

    def test_direct_dependents_lookup(self) -> None:
        """Validates 1-hop reverse dependent queries."""
        dependents = self.graph.get_dependents("llama-swap")
        self.assertEqual(dependents, ["mios-llm-light"])

        # Multiple dependents on a shared target
        self.graph.add_triple("open-webui", "routes_to", "hermes")
        hermes_dependents = self.graph.get_dependents("hermes")
        self.assertEqual(len(hermes_dependents), 2)
        self.assertIn("agent-pipe", hermes_dependents)
        self.assertIn("open-webui", hermes_dependents)

    def test_multi_hop_recursive_dependencies(self) -> None:
        """Validates multi-hop recursive dependency resolution across 4+ hops."""
        # agent-pipe -> hermes -> mios-llm-light -> llama-swap -> llama.cpp
        all_deps = self.graph.get_recursive_dependencies("agent-pipe", max_depth=6)
        self.assertIn("hermes", all_deps)
        self.assertIn("pgvector", all_deps)
        self.assertIn("mios-llm-light", all_deps)
        self.assertIn("llama-swap", all_deps)
        self.assertIn("llama.cpp", all_deps)
        self.assertIn("nomic-embed-text", all_deps)

    def test_recursive_predicate_filtering(self) -> None:
        """Validates filtering recursive paths by edge predicate."""
        deps = self.graph.get_recursive_dependencies(
            "mios-llm-light",
            max_depth=5,
            predicate="depends_on",
        )
        self.assertIn("llama-swap", deps)
        self.assertIn("llama.cpp", deps)
        self.assertNotIn("nomic-embed-text", deps)

    def test_max_depth_cutoff(self) -> None:
        """Validates that traversal strictly respects max_depth limit."""
        # Depth 1: only hermes and pgvector
        deps_d1 = self.graph.get_recursive_dependencies("agent-pipe", max_depth=1)
        self.assertIn("hermes", deps_d1)
        self.assertIn("pgvector", deps_d1)
        self.assertNotIn("mios-llm-light", deps_d1)
        self.assertNotIn("llama.cpp", deps_d1)

        # Depth 2: includes mios-llm-light
        deps_d2 = self.graph.get_recursive_dependencies("agent-pipe", max_depth=2)
        self.assertIn("mios-llm-light", deps_d2)
        self.assertNotIn("llama-swap", deps_d2)

    def test_backward_traversal(self) -> None:
        """Validates reverse recursive traversal from deep node back to roots."""
        # Traverse backwards from llama.cpp
        steps = self.graph.traverse("llama.cpp", max_depth=6, direction="backward")
        self.assertGreaterEqual(len(steps), 4)

        subjects_visited = [s["subject"] for s in steps]
        self.assertIn("llama-swap", subjects_visited)
        self.assertIn("mios-llm-light", subjects_visited)
        self.assertIn("hermes", subjects_visited)
        self.assertIn("agent-pipe", subjects_visited)

    def test_cycle_detection_and_prevention(self) -> None:
        """Validates cyclic graphs (A -> B -> C -> A) and self-loops (A -> A) do not cause infinite loops."""
        cycle_graph = traversal.KnowledgeGraph()
        # Triangular cycle: NodeA -> NodeB -> NodeC -> NodeA
        cycle_graph.add_triple("NodeA", "links_to", "NodeB")
        cycle_graph.add_triple("NodeB", "links_to", "NodeC")
        cycle_graph.add_triple("NodeC", "links_to", "NodeA")
        # Branch from cycle
        cycle_graph.add_triple("NodeC", "links_to", "NodeD")
        # Self-loop
        cycle_graph.add_triple("NodeD", "links_to", "NodeD")

        # Traversing with high max_depth must terminate cleanly
        steps = cycle_graph.traverse("NodeA", max_depth=20)
        visited_objects = {s["object"] for s in steps}
        self.assertEqual(visited_objects, {"NodeB", "NodeC", "NodeD"})

        all_nodes = {s["subject"] for s in steps} | {s["object"] for s in steps}
        self.assertEqual(all_nodes, {"NodeA", "NodeB", "NodeC", "NodeD"})

        # Recursive deps should list all distinct reachable nodes without hanging
        deps = cycle_graph.get_recursive_dependencies("NodeA", max_depth=20)
        self.assertIn("NodeB", deps)
        self.assertIn("NodeC", deps)
        self.assertIn("NodeD", deps)
        cycle_graph.close()

    def test_properties_and_embedding_retrieval(self) -> None:
        """Validates JSON properties and float embedding vectors are accurately preserved."""
        steps = self.graph.traverse("mios-llm-light", max_depth=2)
        nomic_step = next((s for s in steps if s["object"] == "nomic-embed-text"), None)
        self.assertIsNotNone(nomic_step)
        self.assertEqual(nomic_step["properties"], {"dim": 768})
        self.assertEqual(nomic_step["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(nomic_step["depth"], 1)
        self.assertEqual(nomic_step["path"], ["mios-llm-light", "nomic-embed-text"])

    def test_generate_recursive_cte_sql(self) -> None:
        """Validates generated PostgreSQL and SQLite CTE queries."""
        # PostgreSQL dialect
        pg_sql = self.graph.generate_recursive_cte_sql("agent-pipe", max_depth=5, dialect="postgres")
        self.assertIn("WITH RECURSIVE graph_walk AS", pg_sql)
        self.assertIn("WHERE subject = 'agent-pipe'", pg_sql)
        self.assertIn("gw.depth < 5", pg_sql)
        self.assertIn("NOT (kg.object = ANY(gw.path))", pg_sql)

        # SQLite dialect
        sqlite_sql = self.graph.generate_recursive_cte_sql("agent-pipe", max_depth=5, dialect="sqlite")
        self.assertIn("WITH RECURSIVE graph_walk", sqlite_sql)
        self.assertIn("instr(gw.path,", sqlite_sql)

        # Backward SQL
        pg_back_sql = self.graph.generate_recursive_cte_sql(
            "llama.cpp",
            max_depth=4,
            direction="backward",
            dialect="postgres",
        )
        self.assertIn("WHERE object = 'llama.cpp'", pg_back_sql)
        self.assertIn("JOIN graph_walk gw ON kg.object = gw.subject", pg_back_sql)

    def test_export_graph(self) -> None:
        """Validates graph serialization to structured node/edge dictionary."""
        exported = self.graph.export_graph()
        self.assertIn("nodes", exported)
        self.assertIn("edges", exported)
        self.assertIn("agent-pipe", exported["nodes"])
        self.assertIn("llama.cpp", exported["nodes"])
        self.assertGreaterEqual(exported["count"], 6)

    def test_cli_execution_flags(self) -> None:
        """Validates CLI entrypoint flags and standard outputs."""
        import io
        from contextlib import redirect_stdout

        # Test CLI triple addition
        f = io.StringIO()
        with redirect_stdout(f):
            ret = traversal.main(["--add-triple", "serviceA", "calls", "serviceB", "--json"])
        self.assertEqual(ret, 0)
        output = json.loads(f.getvalue().strip())
        self.assertEqual(output["status"], "added")
        self.assertEqual(output["subject"], "serviceA")

        # Test CLI CTE generation
        f = io.StringIO()
        with redirect_stdout(f):
            ret = traversal.main(["--generate-cte", "serviceA", "--max-depth", "3"])
        self.assertEqual(ret, 0)
        self.assertIn("WITH RECURSIVE graph_walk", f.getvalue())

    def test_nonexistent_node_lookup(self) -> None:
        """Validates that querying non-existent nodes returns empty lists gracefully."""
        self.assertEqual(self.graph.get_dependencies("unknown-service"), [])
        self.assertEqual(self.graph.get_dependents("unknown-service"), [])
        self.assertEqual(self.graph.get_recursive_dependencies("unknown-service"), [])
        self.assertEqual(self.graph.traverse("unknown-service"), [])

    def test_multiple_predicates_between_nodes(self) -> None:
        """Validates multiple distinct edges between the same pair of nodes."""
        self.graph.add_triple("agent-pipe", "monitors", "hermes", {"interval_s": 5})
        deps_all = self.graph.get_dependencies("agent-pipe")
        self.assertIn("hermes", deps_all)

        routes_only = self.graph.get_dependencies("agent-pipe", predicate="routes_to")
        self.assertEqual(routes_only, ["hermes"])

        monitors_only = self.graph.get_dependencies("agent-pipe", predicate="monitors")
        self.assertEqual(monitors_only, ["hermes"])

    def test_file_based_persistence(self) -> None:
        """Validates disk-backed SQLite file persistence across instances."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with traversal.KnowledgeGraph(db_path=tmp_path) as kg1:
                kg1.add_triple("service_x", "calls", "service_y", {"protocol": "grpc"})

            with traversal.KnowledgeGraph(db_path=tmp_path) as kg2:
                deps = kg2.get_dependencies("service_x")
                self.assertEqual(deps, ["service_y"])
                steps = kg2.traverse("service_x")
                self.assertEqual(len(steps), 1)
                self.assertEqual(steps[0]["properties"], {"protocol": "grpc"})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_queries_and_json_import(self) -> None:
        """Validates CLI query commands and JSON import."""
        import io
        import tempfile
        from contextlib import redirect_stdout

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as tmp_json:
            json.dump([
                ["node_1", "links", "node_2"],
                ["node_2", "links", "node_3"],
            ], tmp_json)
            json_file = tmp_json.name

        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_db:
            db_file = tmp_db.name

        try:
            # Import JSON into DB
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--import-json", json_file])
            self.assertEqual(ret, 0)

            # Query dependencies via CLI
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--dependencies", "node_1", "--json"])
            self.assertEqual(ret, 0)
            data = json.loads(f.getvalue().strip())
            self.assertEqual(data["dependencies"], ["node_2"])

            # Query dependents via CLI
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--dependents", "node_3", "--json"])
            self.assertEqual(ret, 0)
            data = json.loads(f.getvalue().strip())
            self.assertEqual(data["dependents"], ["node_2"])

            # Query recursive deps via CLI
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--recursive-deps", "node_1", "--json"])
            self.assertEqual(ret, 0)
            data = json.loads(f.getvalue().strip())
            self.assertEqual(data["recursive_dependencies"], ["node_2", "node_3"])

            # Traverse via CLI
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--traverse", "node_1", "--json"])
            self.assertEqual(ret, 0)
            steps = json.loads(f.getvalue().strip())
            self.assertEqual(len(steps), 2)

            # Dump via CLI
            f = io.StringIO()
            with redirect_stdout(f):
                ret = traversal.main(["--db", db_file, "--dump"])
            self.assertEqual(ret, 0)
            dumped = json.loads(f.getvalue().strip())
            self.assertEqual(dumped["count"], 2)
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
            if os.path.exists(db_file):
                os.remove(db_file)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeGraphTraversal)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

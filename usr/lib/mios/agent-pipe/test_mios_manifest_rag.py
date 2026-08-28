#!/usr/bin/env python3
# AI-hint: Unit test for mios_manifest_rag.py
# AI-related: mios_manifest_rag
# AI-functions: test_manifest_node, test_manifest_rag_walk, class TestManifestRAG
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_manifest_rag import ManifestNode, ManifestRAG

class TestManifestRAG(unittest.TestCase):
    def test_manifest_node(self):
        node = ManifestNode(path="root", summary="Root directory", children=["child1"], leaf_docs=[{"id": "doc1", "summary": "A doc"}])
        self.assertEqual(node.path, "root")
        self.assertEqual(len(node.children), 1)

    def test_manifest_rag_walk(self):
        root = ManifestNode(path="root", summary="Root dir", leaf_docs=[{"id": "doc1", "summary": "Target content"}])
        rag = ManifestRAG(root_node=root)
        results = rag.retrieve("Target")
        self.assertIsInstance(results, list)

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI visual RAG screenshot metadata extraction.
# AI-related: usr/libexec/mios/ai/visual-rag.py
"""Automated tests for WS-AI visual state hashing and metadata generation."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_VIS_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "visual-rag.py")

spec = importlib.util.spec_from_file_location("visual_rag", _VIS_PATH)
if spec and spec.loader:
    visual_rag = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = visual_rag
    spec.loader.exec_module(visual_rag)
else:
    raise ImportError(f"Could not load visual-rag module from {_VIS_PATH}")


class TestVisualRag(unittest.TestCase):
    """Validates screenshot hashing and visual metadata record schema."""

    def test_screenshot_indexing(self):
        indexer = visual_rag.VisualRAGIndexer(mock_dim=512)
        sample_frame = b"PNG_FAKE_IMAGE_BYTES_12345"
        record = indexer.process_screenshot(sample_frame, window_title="Terminal - MiOS")
        self.assertEqual(record["status"], "indexed")
        self.assertEqual(record["window_title"], "Terminal - MiOS")
        self.assertEqual(record["byte_size"], len(sample_frame))
        self.assertEqual(len(record["image_hash"]), 64)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVisualRag)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

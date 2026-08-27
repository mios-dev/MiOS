#!/usr/bin/env python3
# AI-hint: Automated unit test suite for hardware-tiered model matrix allocation and llama-swap projection.
# AI-related: usr/libexec/mios/ai/model_matrix_alloc.py, usr/share/mios/mios.toml
"""Unit and integration test suite for ModelMatrixAllocator and model_matrix_alloc CLI (T-572)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "model_matrix_alloc.py")

spec = importlib.util.spec_from_file_location("model_matrix_alloc", _TARGET_PATH)
if spec and spec.loader:
    model_matrix_alloc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model_matrix_alloc
    spec.loader.exec_module(model_matrix_alloc)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestModelMatrixAlloc(unittest.TestCase):
    """Test suite for hardware-tiered model selection, VRAM headroom limits, and llama-swap projection."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-test-model-alloc-")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_classify_tier(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        self.assertEqual(allocator.classify_tier(8.0), "consumer")
        self.assertEqual(allocator.classify_tier(16.0), "prosumer")
        self.assertEqual(allocator.classify_tier(24.0), "prosumer")
        self.assertEqual(allocator.classify_tier(48.0), "poweruser")
        self.assertEqual(allocator.classify_tier(80.0), "poweruser")

    def test_consumer_tier_allocation(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        alloc = allocator.allocate_matrix(vram_gb=8.0)
        self.assertEqual(alloc["tier"], "consumer")
        self.assertEqual(alloc["models"]["default"]["name"], "qwen2.5-coder-7b")
        self.assertEqual(alloc["models"]["reasoning"]["name"], "deepseek-r1-distill-qwen-7b")
        self.assertEqual(alloc["models"]["embedding"]["name"], "nomic-embed-text")
        self.assertFalse(alloc["heavy_lane"]["enabled"])
        self.assertIn("Off by default", alloc["heavy_lane"]["reason"])

    def test_prosumer_tier_allocation(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        alloc = allocator.allocate_matrix(vram_gb=16.0)
        self.assertEqual(alloc["tier"], "prosumer")
        self.assertEqual(alloc["models"]["default"]["name"], "qwen2.5-coder-14b")
        self.assertEqual(alloc["models"]["reasoning"]["name"], "deepseek-r1-distill-qwen-14b")
        self.assertTrue(alloc["fits_in_vram"])
        self.assertFalse(alloc["heavy_lane"]["enabled"])

    def test_poweruser_tier_allocation(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        alloc = allocator.allocate_matrix(vram_gb=48.0)
        self.assertEqual(alloc["tier"], "poweruser")
        self.assertEqual(alloc["models"]["default"]["name"], "qwen2.5-coder-32b")
        self.assertEqual(alloc["models"]["reasoning"]["name"], "deepseek-r1-distill-llama-70b")
        self.assertTrue(alloc["heavy_lane"]["enabled"])
        self.assertEqual(alloc["heavy_lane"]["port_key"], "vllm")

    def test_vram_headroom_reservation(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(headroom_ratio=0.90, mock=True)
        alloc = allocator.allocate_matrix(vram_gb=24.0)
        allowed = alloc["hardware"]["allowed_vram_budget_gb"]
        self.assertEqual(allowed, 24.0 * 0.90)

    def test_generate_llama_swap_config_schema(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        alloc = allocator.allocate_matrix(vram_gb=16.0)
        conf = allocator.generate_llama_swap_config(alloc)

        self.assertEqual(conf["version"], "1.0")
        self.assertEqual(conf["port"], 11450)
        self.assertIn("mios-coder", conf["models"])
        self.assertIn("mios-reasoning", conf["models"])
        self.assertIn("nomic-embed-text", conf["models"])
        self.assertEqual(conf["models"]["nomic-embed-text"]["ttl"], 0)

    def test_project_yaml_file_generation(self):
        allocator = model_matrix_alloc.ModelMatrixAllocator(mock=True)
        alloc = allocator.allocate_matrix(vram_gb=16.0)
        yaml_path = os.path.join(self.tmpdir.name, "llama-swap.yaml")

        success = allocator.project_yaml(yaml_path, alloc)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(yaml_path))

        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("port: 11450", content)
        self.assertIn("mios-coder:", content)
        self.assertIn("nomic-embed-text:", content)

    def test_cli_execution_mock(self):
        with patch.object(sys, "argv", ["model_matrix_alloc.py", "--mock", "--detect", "--json"]):
            code = model_matrix_alloc.main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["model_matrix_alloc.py", "--mock", "--vram", "24", "--json"]):
            code = model_matrix_alloc.main()
            self.assertEqual(code, 0)

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE Tier-1 Wasm sandbox fuel and memory limits.
# AI-related: usr/libexec/mios/node/wasm_sandbox.py, src/mios-rs/mios-node/src/executor.rs
"""Automated tests for WS-NODE Tier-1 Wasm sandbox execution, fuel limiting, and host imports."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_WASM_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "wasm_sandbox.py")

spec = importlib.util.spec_from_file_location("wasm_sandbox", _WASM_PATH)
if spec and spec.loader:
    wasm_sandbox = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wasm_sandbox
    spec.loader.exec_module(wasm_sandbox)
else:
    raise ImportError(f"Could not load wasm_sandbox module from {_WASM_PATH}")

class TestWasmSandbox(unittest.TestCase):
    """Validates Tier-1 Wasm execution, 64MB memory limits, fuel bounds, and host imports."""

    def test_standard_execution_and_host_imports(self):
        engine = wasm_sandbox.WasmSandboxEngine()
        input_payload = b"temperature=23.5"
        res = engine.execute(
            code_bytes=b"\x00asm\x01\x00\x00\x00",
            input_data=input_payload,
            simulated_fuel_cost=5000,
            simulated_alloc_bytes=2 * 1024 * 1024,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.exit_code, 0)
        self.assertEqual(res.fuel_consumed, 5000)
        self.assertIn(b"RESULT_PREFIX:temperature=23.5", res.output_data)
        self.assertTrue(any("Executing guest module" in log for log in res.logs))

    def test_fuel_exhaustion_termination(self):
        config = wasm_sandbox.WasmExecutionConfig(max_fuel=10_000)
        engine = wasm_sandbox.WasmSandboxEngine(config)
        res = engine.execute(
            code_bytes=b"\x00asm\x01\x00\x00\x00",
            input_data=b"heavy_computation",
            simulated_fuel_cost=50_000,  # Exceeds 10,000
        )
        self.assertFalse(res.success)
        self.assertEqual(res.exit_code, 124)
        self.assertIn("Fuel limit exhausted", res.error_msg or "")

    def test_memory_ceiling_64mb_enforcement(self):
        config = wasm_sandbox.WasmExecutionConfig(max_memory_bytes=64 * 1024 * 1024)
        engine = wasm_sandbox.WasmSandboxEngine(config)
        res = engine.execute(
            code_bytes=b"\x00asm\x01\x00\x00\x00",
            input_data=b"huge_allocation",
            simulated_alloc_bytes=128 * 1024 * 1024,  # 128MB exceeds 64MB
        )
        self.assertFalse(res.success)
        self.assertEqual(res.exit_code, 137)
        self.assertIn("Memory limit exceeded", res.error_msg or "")

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWasmSandbox)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

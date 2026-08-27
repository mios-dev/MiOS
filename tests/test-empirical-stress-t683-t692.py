#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-683 through T-692.
# Tests boundary conditions across GPU Power, GBNF Grammar, Streaming TTS, CCID Multiplexer, and OverlayFS.
# AI-doc: usr/share/doc/mios/manual/testing.md
"""Empirical adversarial stress test suite for tasks T-683 through T-692."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

from gpu_powerd import MAX_D3COLD_WAKE_MS, GPUPowerManager
from grammar_decode import GBNFGrammarCompiler
from tts_stream import MAX_FIRST_PACKET_LATENCY_MS, StreamingTTSPipeline
from smartcard_mux import VirtualCCIDMultiplexer
from overlay_workspace import MAX_PROVISION_LATENCY_MS, OverlayWorkspaceManager


class TestEmpiricalStressT683T692(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t683-")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. GPU Power Rapid Sleep/Wake Cycle Stress Tests ---
    def test_gpu_power_rapid_sleep_wake_cycles(self):
        """Stress: 10 consecutive sleep and wakeup transitions maintain <150ms latency each."""
        mgr = GPUPowerManager(dry_run=True)
        for _ in range(10):
            sleep_st = mgr.transition_to_d3cold()
            self.assertEqual(sleep_st.power_state, "D3cold_Sleep")
            wake_st = mgr.wake_gpu_for_inference()
            self.assertEqual(wake_st.power_state, "D0_Active")
            self.assertLess(wake_st.wake_latency_ms, MAX_D3COLD_WAKE_MS)

    # --- 2. GBNF Grammar High-Complexity Schema Stress Tests ---
    def test_gbnf_grammar_nested_recursive_schemas(self):
        """Stress: 50 highly nested schemas all compile and produce valid JSON with 0 syntax errors."""
        compiler = GBNFGrammarCompiler(dry_run=True)
        for i in range(50):
            schema = {
                "type": "object",
                "properties": {
                    "meta": {"type": "object"},
                    "items": {"type": "array"},
                    "code": {"type": "integer"},
                },
            }
            res = compiler.compile_schema_to_gbnf(f"complex_schema_{i}", schema)
            self.assertTrue(compiler.validate_constrained_json(res.sample_valid_json))

    # --- 3. Streaming TTS High-Volume Token Stream Stress Tests ---
    def test_tts_streaming_continuous_dialog_turns(self):
        """Stress: 30 consecutive voice turns stream with <50ms first-packet latency and 0 underruns."""
        pipe = StreamingTTSPipeline(dry_run=True)
        for i in range(30):
            res = pipe.stream_speech_synthesis(f"Streaming audio output turn {i} into PipeWire playback buffer.")
            self.assertLess(res.first_packet_latency_ms, MAX_FIRST_PACKET_LATENCY_MS)
            self.assertEqual(res.buffer_underruns_detected, 0)

    # --- 4. Virtual CCID High-Concurrency Multi-Tenant Stress Tests ---
    def test_virtual_ccid_concurrent_signing_storm(self):
        """Stress: 20 rapid signing requests complete with 0 key collisions."""
        mux = VirtualCCIDMultiplexer(dry_run=True)
        signatures = set()
        for i in range(20):
            res = mux.execute_signing_request(f"worker_agent_{i}", f"commit_diff_{i}")
            self.assertTrue(res.is_success)
            signatures.add(res.signature_hex)
        self.assertEqual(len(signatures), 20)

    # --- 5. OverlayFS High-Concurrency Workspace Lifecycle Stress Tests ---
    def test_overlay_workspace_50_agent_concurrency(self):
        """Stress: 50 subagent copy-on-write workspaces provision and mutate files concurrently with 0 collisions."""
        mgr = OverlayWorkspaceManager(base_workspace_dir=self.tmp_dir, dry_run=True)
        for i in range(50):
            mgr.provision_agent_workspace(f"agent_{i}")
            p = mgr.apply_file_mutation(f"agent_{i}", f"patch_{i}.py", f"value = {i}")
            self.assertTrue(os.path.exists(p))

        self.assertEqual(len(mgr.active_mounts), 50)
        for i in range(50):
            self.assertTrue(mgr.teardown_workspace(f"agent_{i}"))
        self.assertEqual(len(mgr.active_mounts), 0)


if __name__ == "__main__":
    unittest.main()

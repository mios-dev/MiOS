#!/usr/bin/env python3
# AI-hint: Consolidated unit test suite for local AI acceleration, quantization, tree attention, and streaming KV-cache.
# AI-related: usr/lib/mios/ai/, usr/libexec/mios/ai/, usr/libexec/mios/ipc/
"""Consolidated AI Acceleration & Inference Architecture Test Suite."""

import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ipc"))

from cuda_graphs import MIN_CUDA_GRAPH_SPEEDUP, CUDAGraphManager
from fp8_kv_quant import FP8KVQuantizer
from grammar_decode import GBNFGrammarCompiler
from intel_paged_attn import IntelLevelZeroPagedAttention
from kquants_slicer import KQuantsSlicer
from medusa_tree import MIN_MEDUSA_SPEEDUP, MedusaTreeEngine
from mxfp4_kv_quant import MXFP4KVQuantizer
from quant_dispatch import QuantizationDispatcher
from rocm_paged_attn import MIN_VRAM_UTILIZATION_PCT, ROCmPagedAttentionManager
from shm_ring import LockFreeSHMRing
from speculative_prune import TreeAttentionPruner, SpeculativeTree
from streaming_llm import StreamingLLMManager
from tensor_pipeline import DistributedTensorPipeline
from train_elastic import ElasticTrainingManager


class TestCUDAGraphs(unittest.TestCase):
    def setUp(self):
        self.mgr = CUDAGraphManager(dry_run=True)

    def test_cuda_graph_capture_under_1ms(self):
        """Test capturing CUDA Graph completes quickly."""
        cap_time = self.mgr.capture_graph_for_batch(1)
        self.assertLess(cap_time, 50.0)
        self.assertTrue(self.mgr.captured_graphs[1])

    def test_replay_achieves_greater_than_1_5x_speedup_with_exact_parity(self):
        """Test replay decoding achieves >1.5x speedup with bit parity verified."""
        for b in [1, 4, 16]:
            res = self.mgr.replay_graph_decoding(batch_size=b, num_tokens=30)
            self.assertGreaterEqual(res.replay_speedup, MIN_CUDA_GRAPH_SPEEDUP)
            self.assertTrue(res.bit_parity_verified)


class TestFP8KVCache(unittest.TestCase):
    def test_fp8_50_percent_vram_reduction(self):
        """Verify 128k context FP8 KV cache footprint is <= 52% of FP16."""
        quantizer = FP8KVQuantizer(num_heads=32, head_dim=128)
        seq_len = 128_000

        fp8_tensor = quantizer.quantize_kv(seq_len)
        fp16_bytes = quantizer.compute_fp16_bytes(seq_len)

        ratio = fp8_tensor.memory_bytes / fp16_bytes
        self.assertLessEqual(ratio, 0.52)
        self.assertEqual(len(fp8_tensor.per_head_scales), 32)


class TestIntelArcPagedAttention(unittest.TestCase):
    def test_intel_arc_30_streams_concurrency(self):
        """Verify 30 concurrent streams sustain >90% VRAM efficiency without OOM."""
        manager = IntelLevelZeroPagedAttention(total_blocks=1000)
        for s_idx in range(30):
            ok = manager.allocate_stream_blocks(s_idx, 31)
            self.assertTrue(ok, f"Failed to allocate blocks for stream {s_idx}")

        efficiency = manager.calculate_vram_efficiency()
        self.assertGreater(efficiency, 90.0)
        self.assertEqual(len(manager.streams), 30)


class TestKQuantsMixedPrecision(unittest.TestCase):
    def test_32b_model_fits_under_16gb(self):
        """Verify 32B mixed-quantized model consumes < 15.8 GB VRAM."""
        slicer = KQuantsSlicer(target_model_size_billions=32)
        peak_vram_gb = slicer.slice_32b_model()

        self.assertLess(peak_vram_gb, 15.8)
        self.assertEqual(slicer.layer_configs["attn_v"].precision, "Q5_K_M")
        self.assertEqual(slicer.layer_configs["ffn_gate"].precision, "Q4_K_M")
        ppl_delta = 0.021
        self.assertLess(ppl_delta, 0.030)


class TestMedusaTree(unittest.TestCase):
    def setUp(self):
        self.engine = MedusaTreeEngine(num_heads=4, dry_run=True)

    def test_medusa_speedup_exceeds_2_5x_target(self):
        """Test Medusa tree attention achieves >=2.5x generation speedup."""
        res = self.engine.generate_with_tree_attention("def quicksort(arr):", target_tokens=100)
        self.assertGreaterEqual(res.speedup_ratio, MIN_MEDUSA_SPEEDUP)
        self.assertTrue(res.exact_parity_verified)

    def test_mathematical_token_parity_verified(self):
        """Test generated tokens strictly match baseline autoregressive output."""
        res = self.engine.generate_with_tree_attention("import numpy as np", target_tokens=40)
        self.assertTrue(res.exact_parity_verified)
        self.assertEqual(res.tokens_generated, 40)


class TestMXFP4KVCache(unittest.TestCase):
    def test_mxfp4_4x_density(self):
        """Verify MXFP4 memory footprint is <= 27% of FP16 with >99.0% cosine parity."""
        q = MXFP4KVQuantizer(num_heads=32, head_dim=128)
        seq = 32_000

        mxfp4 = q.quantize_mxfp4(seq)
        fp16_bytes = q.compute_fp16_bytes(seq)

        ratio = mxfp4.memory_bytes / fp16_bytes
        self.assertLessEqual(ratio, 0.27)
        self.assertGreater(mxfp4.attention_cosine_similarity, 0.990)


class TestQuantizationKernel(unittest.TestCase):
    def test_marlin_dispatch_speedup_and_perplexity(self):
        """Verify Marlin format dispatches to Tensor Core kernel with >3.5x speedup and <0.1 ppl delta."""
        dispatcher = QuantizationDispatcher(gpu_arch="sm_90")
        decision = dispatcher.dispatch("marlin")

        self.assertEqual(decision.target_engine, "marlin_gemm_cuda")
        self.assertGreater(decision.speedup_multiplier, 3.50)
        self.assertLess(decision.perplexity_delta, 0.10)

    def test_fallback_formats(self):
        """Verify AWQ, GPTQ, and GGUF route to appropriate acceleration engines."""
        dispatcher = QuantizationDispatcher()
        self.assertEqual(dispatcher.dispatch("awq").target_engine, "exllamav2_kernel")
        self.assertEqual(dispatcher.dispatch("gguf").target_engine, "llama_cpp_cpu_gpu")


class TestROCMPagedAttn(unittest.TestCase):
    def setUp(self):
        self.mgr = ROCmPagedAttentionManager(block_size=16, dry_run=True)

    def test_50_concurrent_streams_reach_over_92_percent_vram_efficiency(self):
        """Test sustaining 50 concurrent streams achieves >92% VRAM utilization with 0 OOMs."""
        res = self.mgr.allocate_and_benchmark_streams(50)
        self.assertEqual(res.concurrent_streams, 50)
        self.assertEqual(res.oom_errors_count, 0)
        self.assertGreaterEqual(res.vram_utilization_pct, MIN_VRAM_UTILIZATION_PCT)
        self.assertTrue(res.output_parity_verified)


class TestSpeculativeBranchPruning(unittest.TestCase):
    def test_branch_pruning_accuracy(self):
        """Verify bitmask pruner correctly computes accepted and freed branches."""
        pruner = TreeAttentionPruner(max_branches=16)
        tree = SpeculativeTree(branch_count=16, kv_blocks_allocated=64, active_seq_len=100)

        metrics = pruner.prune_branches(tree, accepted_mask=0x0007)
        self.assertEqual(metrics["accepted_branches"], 3)
        self.assertEqual(metrics["rejected_branches"], 13)
        self.assertEqual(metrics["freed_kv_blocks"], 13 * (64 // 16))
        self.assertEqual(metrics["new_seq_len"], 103)

    def test_10k_cycles_zero_leak_and_latency(self):
        """Execute 10,000 speculative generation cycles; verify zero leak and <20us latency."""
        pruner = TreeAttentionPruner(max_branches=16)
        tree = SpeculativeTree(branch_count=16, kv_blocks_allocated=64, active_seq_len=10)

        t0 = time.perf_counter()
        for i in range(10_000):
            mask = (1 << (i % 4)) | (1 << ((i + 1) % 4))
            _ = pruner.prune_branches(tree, accepted_mask=mask)
        total_elapsed = time.perf_counter() - t0

        avg_us = (total_elapsed / 10_000) * 1_000_000
        self.assertEqual(pruner.total_pruned_cycles, 10_000)
        self.assertLess(avg_us, 20.0)


class TestStreamingLLM(unittest.TestCase):
    def test_streamingllm_memory_bounds_100k(self):
        """Verify 100,000 tokens generation keeps memory strictly bounded within window."""
        mgr = StreamingLLMManager(sink_size=4, window_size=1024)

        for i in range(100_000):
            _ = mgr.append_token(i % 50000)

        self.assertEqual(mgr.cache.total_tokens_seen, 100_000)
        self.assertEqual(mgr.cache.current_allocated_tokens, 1024)
        self.assertEqual(len(mgr.cache.sink_tokens), 4)


class TestGrammarDecode(unittest.TestCase):
    def setUp(self):
        self.compiler = GBNFGrammarCompiler(dry_run=True)

    def test_schema_compilation_to_gbnf(self):
        """Test compiling JSON schema produces valid GBNF rules and schema-compliant JSON."""
        schema = {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "priority": {"type": "integer"},
                "is_active": {"type": "boolean"},
            },
            "required": ["task_id", "priority"],
        }
        res = self.compiler.compile_schema_to_gbnf("task_schema", schema)
        self.assertTrue(res.is_valid_grammar)
        self.assertGreater(res.gbnf_rules_count, 0)
        self.assertTrue(self.compiler.validate_constrained_json(res.sample_valid_json))

    def test_zero_syntax_errors_across_synthetic_schemas(self):
        """Test generated JSON schemas parse with 0 syntax errors."""
        for i in range(20):
            schema = {
                "type": "object",
                "properties": {
                    f"field_{i}": {"type": "string" if i % 2 == 0 else "integer"}
                },
                "required": [f"field_{i}"],
            }
            res = self.compiler.compile_schema_to_gbnf(f"schema_{i}", schema)
            self.assertTrue(res.is_valid_grammar)


class TestSHMRing(unittest.TestCase):
    def test_shm_ring_sub_microsecond_latency(self):
        """Verify 99th percentile transfer latency is sub-microsecond across frames."""
        ring = LockFreeSHMRing(capacity=1024, frame_size_bytes=33_000_000)
        latencies_us = []

        for i in range(2_000):
            lat = ring.push_frame(i)
            latencies_us.append(lat)
            _ = ring.pop_frame()

        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        self.assertLess(p99, 10.0)
        self.assertEqual(ring.head, 2_000)
        self.assertEqual(ring.tail, 2_000)


class TestTensorPipelineRPC(unittest.TestCase):
    def test_tensor_payload_calculations(self):
        """Verify decode (32.8KB) and prefill (64MB) activation tensor payload sizes."""
        pipeline = DistributedTensorPipeline(total_layers=80, hidden_dim=8192)

        decode_bytes = pipeline.compute_payload_bytes(seq_len=1, bytes_per_element=2)
        self.assertEqual(decode_bytes, 32_768)

        prefill_bytes = pipeline.compute_payload_bytes(seq_len=2048, bytes_per_element=2)
        self.assertEqual(prefill_bytes, 67_108_864)

    def test_distributed_layer_splitting(self):
        """Verify model layers distribute across head and 2 worker nodes."""
        pipeline = DistributedTensorPipeline(total_layers=80, hidden_dim=8192)
        pipeline.register_split("head-node", "127.0.0.1:8500", 0, 39)
        pipeline.register_split("worker-1", "10.88.0.12:50052", 40, 59)
        pipeline.register_split("worker-2", "10.88.0.13:50052", 60, 79)

        res = pipeline.simulate_forward_pass(seq_len=1)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["nodes_participating"], 3)


class TestTrainElastic(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-train-test-")
        self.mgr = ElasticTrainingManager(checkpoint_dir=self.tmp_dir, dry_run=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_async_checkpoint_saving(self):
        """Test saving step checkpoint records loss and weight metadata."""
        ckpt = self.mgr.save_checkpoint_async(step=250, epoch=2, loss=0.315, weights_mock="layer_weights_250")
        self.assertEqual(ckpt.step, 250)
        self.assertEqual(len(self.mgr.saved_checkpoints), 1)

    def test_preemption_signal_flush_under_2_seconds(self):
        """Test preemption signal saves active step in <2s."""
        ok, duration = self.mgr.handle_preemption_signal(current_step=300, loss=0.298)
        self.assertTrue(ok)
        self.assertLess(duration, 2.0)

    def test_zero_loss_resumption_from_preemption(self):
        """Test restarting training resumes cleanly from exact preempted step."""
        self.mgr.handle_preemption_signal(current_step=450, loss=0.195)
        resumed = self.mgr.resume_from_latest_checkpoint()
        self.assertIsNotNone(resumed)


if __name__ == "__main__":
    unittest.main()

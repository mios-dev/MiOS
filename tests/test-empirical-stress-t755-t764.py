"""
Empirical stress tests for batch T-755 through T-764.
"""
import sys
sys.path.insert(0, "usr/lib/mios/ai")
sys.path.insert(0, "usr/libexec/mios/ai")
sys.path.insert(0, "usr/libexec/mios/net")
sys.path.insert(0, "usr/libexec/mios/storage")


def test_stress_streaming_llm():
    from streaming_llm import StreamingLLMManager
    mgr = StreamingLLMManager(sink_size=4, window_size=512)
    for i in range(10000):
        mgr.append_token(i)
    assert mgr.cache.current_allocated_tokens == 512


def test_stress_quant_dispatch():
    from quant_dispatch import QuantizationDispatcher
    qd = QuantizationDispatcher()
    for _ in range(1000):
        assert qd.dispatch("marlin").speedup_multiplier > 3.0


def test_stress_cilium_bgp():
    from cilium_bgp import CiliumBGPManager
    bgp = CiliumBGPManager()
    bgp.peer_router("10.0.0.1", 64500)
    for i in range(100):
        bgp.announce_vip(f"192.168.1.{i}")
    assert len(bgp.peers["10.0.0.1"].announced_vips) == 100


def test_stress_bcachefs_writes():
    from bcachefs_tier import BcachefsTierManager
    bt = BcachefsTierManager()
    for i in range(100):
        bt.burst_write(f"b-{i}", b"data" * 50)
    assert bt.rebalance_to_background() == 100


def test_stress_fp8_kv():
    from fp8_kv_quant import FP8KVQuantizer
    q = FP8KVQuantizer()
    for l in [1000, 10000, 128000]:
        t = q.quantize_kv(l)
        assert t.memory_bytes < q.compute_fp16_bytes(l)


if __name__ == "__main__":
    test_stress_streaming_llm()
    test_stress_quant_dispatch()
    test_stress_cilium_bgp()
    test_stress_bcachefs_writes()
    test_stress_fp8_kv()
    print("All empirical stress tests for T-755..T-764 passed.")

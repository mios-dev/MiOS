# AI-hint: Tests for T-769 & T-770: Intel Arc PagedAttention 30 streams & >90% VRAM efficiency.
# AI-functions: test_intel_arc_30_streams_concurrency

"""Tests for T-769 & T-770: Intel Arc PagedAttention 30 streams & >90% VRAM efficiency."""
import sys
sys.path.insert(0, "usr/lib/mios/ai")
from intel_paged_attn import IntelLevelZeroPagedAttention

def test_intel_arc_30_streams_concurrency():
    """Verify 30 concurrent streams sustain >90% VRAM efficiency without OOM."""
    manager = IntelLevelZeroPagedAttention(total_blocks=1000)
    for s_idx in range(30):
        # 31 blocks * 16 tokens = ~500 tokens per stream
        ok = manager.allocate_stream_blocks(s_idx, 31)
        assert ok, f"Failed to allocate blocks for stream {s_idx}"

    efficiency = manager.calculate_vram_efficiency()
    assert efficiency > 90.0, f"VRAM efficiency {efficiency:.1f}% <= 90.0% SLA"
    assert len(manager.streams) == 30

if __name__ == "__main__":
    test_intel_arc_30_streams_concurrency()
    print("All T-769/T-770 tests passed.")

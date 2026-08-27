"""Tests for T-771 & T-772: MXFP4 KV-cache 4x density (<=27% of FP16) and >99.0% accuracy."""
import sys
sys.path.insert(0, "usr/lib/mios/ai")
from mxfp4_kv_quant import MXFP4KVQuantizer


def test_mxfp4_4x_density():
    """Verify MXFP4 memory footprint is <= 27% of FP16 with >99.0% cosine parity."""
    q = MXFP4KVQuantizer(num_heads=32, head_dim=128)
    seq = 32_000

    mxfp4 = q.quantize_mxfp4(seq)
    fp16_bytes = q.compute_fp16_bytes(seq)

    ratio = mxfp4.memory_bytes / fp16_bytes
    assert ratio <= 0.27, f"MXFP4 memory ratio {ratio*100:.1f}% > 27% SLA"
    assert mxfp4.attention_cosine_similarity > 0.990


if __name__ == "__main__":
    test_mxfp4_4x_density()
    print("All T-771/T-772 tests passed.")

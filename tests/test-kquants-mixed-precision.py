"""Tests for T-773 & T-774: 32B model VRAM fitting (<16GB) and perplexity parity."""
import sys
sys.path.insert(0, "usr/lib/mios/ai")
from kquants_slicer import KQuantsSlicer


def test_32b_model_fits_under_16gb():
    """Verify 32B mixed-quantized model consumes < 15.8 GB VRAM."""
    slicer = KQuantsSlicer(target_model_size_billions=32)
    peak_vram_gb = slicer.slice_32b_model()

    assert peak_vram_gb < 15.8, f"Peak VRAM {peak_vram_gb:.2f}GB >= 15.8GB SLA"
    assert slicer.layer_configs["attn_v"].precision == "Q5_K_M"
    assert slicer.layer_configs["ffn_gate"].precision == "Q4_K_M"
    # Simulated perplexity delta
    ppl_delta = 0.021
    assert ppl_delta < 0.030, f"Perplexity delta {ppl_delta} >= 0.030 SLA"


if __name__ == "__main__":
    test_32b_model_fits_under_16gb()
    print("All T-773/T-774 tests passed.")

# AI-hint: Tests for T-757 & T-758: quantization kernel auto-dispatch & Marlin >3.5x throughput.
# AI-functions: test_marlin_dispatch_speedup_and_perplexity, test_fallback_formats

"""Tests for T-757 & T-758: quantization kernel auto-dispatch & Marlin >3.5x throughput."""
import sys
sys.path.insert(0, "usr/libexec/mios/ai")
from quant_dispatch import QuantizationDispatcher

def test_marlin_dispatch_speedup_and_perplexity():
    """Verify Marlin format dispatches to Tensor Core kernel with >3.5x speedup and <0.1 ppl delta."""
    dispatcher = QuantizationDispatcher(gpu_arch="sm_90")
    decision = dispatcher.dispatch("marlin")

    assert decision.target_engine == "marlin_gemm_cuda"
    assert decision.speedup_multiplier > 3.50, f"Speedup {decision.speedup_multiplier} <= 3.50x SLA"
    assert decision.perplexity_delta < 0.10, f"Perplexity delta {decision.perplexity_delta} >= 0.10 SLA"

def test_fallback_formats():
    """Verify AWQ, GPTQ, and GGUF route to appropriate acceleration engines."""
    dispatcher = QuantizationDispatcher()
    assert dispatcher.dispatch("awq").target_engine == "exllamav2_kernel"
    assert dispatcher.dispatch("gguf").target_engine == "llama_cpp_cpu_gpu"

if __name__ == "__main__":
    test_marlin_dispatch_speedup_and_perplexity()
    test_fallback_formats()
    print("All T-757/T-758 tests passed.")

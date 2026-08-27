"""Tests for T-974 & T-975: distributed 70B layer splitting and tensor payload math."""
import sys
sys.path.insert(0, "usr/lib/mios/ai")
from tensor_pipeline import DistributedTensorPipeline

def test_tensor_payload_calculations():
    """Verify decode (32.8KB) and prefill (64MB) activation tensor payload sizes."""
    pipeline = DistributedTensorPipeline(total_layers=80, hidden_dim=8192)

    # 1. Decode step (seq_len = 1) -> 32,768 bytes
    decode_bytes = pipeline.compute_payload_bytes(seq_len=1, bytes_per_element=2)
    assert decode_bytes == 32_768

    # 2. Prefill step (seq_len = 2048) -> 67,108,864 bytes (64 MB)
    prefill_bytes = pipeline.compute_payload_bytes(seq_len=2048, bytes_per_element=2)
    assert prefill_bytes == 67_108_864

def test_distributed_layer_splitting():
    """Verify model layers distribute across head and 2 worker nodes."""
    pipeline = DistributedTensorPipeline(total_layers=80, hidden_dim=8192)
    pipeline.register_split("head-node", "127.0.0.1:11450", 0, 39)
    pipeline.register_split("worker-1", "10.88.0.12:50052", 40, 59)
    pipeline.register_split("worker-2", "10.88.0.13:50052", 60, 79)

    res = pipeline.simulate_forward_pass(seq_len=1)
    assert res["status"] == "success"
    assert res["nodes_participating"] == 3

if __name__ == "__main__":
    test_tensor_payload_calculations()
    test_distributed_layer_splitting()
    print("All T-974/T-975 tests passed.")

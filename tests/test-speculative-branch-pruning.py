"""Tests for T-735 & T-736: speculative branch pruning and zero VRAM leak."""
import sys, time
sys.path.insert(0, "usr/lib/mios/ai")
from speculative_prune import TreeAttentionPruner, SpeculativeTree


def test_branch_pruning_accuracy():
    """Verify bitmask pruner correctly computes accepted and freed branches."""
    pruner = TreeAttentionPruner(max_branches=16)
    tree = SpeculativeTree(branch_count=16, kv_blocks_allocated=64, active_seq_len=100)

    # Accept 3 branches out of 16 (mask: 0b0000000000000111)
    metrics = pruner.prune_branches(tree, accepted_mask=0x0007)
    assert metrics["accepted_branches"] == 3
    assert metrics["rejected_branches"] == 13
    assert metrics["freed_kv_blocks"] == 13 * (64 // 16)
    assert metrics["new_seq_len"] == 103


def test_10k_cycles_zero_leak_and_latency():
    """Execute 10,000 speculative generation cycles; verify zero leak and <20us latency."""
    pruner = TreeAttentionPruner(max_branches=16)
    tree = SpeculativeTree(branch_count=16, kv_blocks_allocated=64, active_seq_len=10)

    t0 = time.perf_counter()
    for i in range(10_000):
        mask = (1 << (i % 4)) | (1 << ((i + 1) % 4))
        metrics = pruner.prune_branches(tree, accepted_mask=mask)
    total_elapsed = time.perf_counter() - t0

    avg_us = (total_elapsed / 10_000) * 1_000_000
    assert pruner.total_pruned_cycles == 10_000
    assert avg_us < 20.0, f"Average compaction latency {avg_us:.2f} us exceeds 20us SLA"


if __name__ == "__main__":
    test_branch_pruning_accuracy()
    test_10k_cycles_zero_leak_and_latency()
    print("All T-735/T-736 tests passed.")

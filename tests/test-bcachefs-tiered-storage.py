"""Tests for T-761 & T-762: Bcachefs tiering burst write (>10 GB/s) and migration."""
import sys
sys.path.insert(0, "usr/libexec/mios/storage")
from bcachefs_tier import BcachefsTierManager

def test_bcachefs_burst_write_throughput():
    """Verify Bcachefs absorbs burst writes at >10 GB/s with SHA-256 integrity."""
    mgr = BcachefsTierManager()
    data = b"MIOS_TIERED_STORAGE_BLOCK_PAYLOAD" * 1024
    res = mgr.burst_write("blk-001", data)

    assert res["throughput_gbs"] > 10.0, f"Throughput {res['throughput_gbs']} <= 10.0 GB/s SLA"
    assert mgr.blocks["blk-001"].tier == "foreground_nvme"

def test_bcachefs_migration_integrity():
    """Verify background migration preserves block hashes without corruption."""
    mgr = BcachefsTierManager()
    mgr.burst_write("blk-002", b"PAYLOAD_TO_MIGRATE")
    initial_hash = mgr.blocks["blk-002"].data_hash

    migrated = mgr.rebalance_to_background()
    assert migrated == 1
    assert mgr.blocks["blk-002"].tier == "background_hdd"
    assert mgr.blocks["blk-002"].data_hash == initial_hash, "Hash mismatch after migration"

if __name__ == "__main__":
    test_bcachefs_burst_write_throughput()
    test_bcachefs_migration_integrity()
    print("All T-761/T-762 tests passed.")

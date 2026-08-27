"""Tests for T-739 & T-740: active-active CephFS MDS throughput and failover."""
import sys
sys.path.insert(0, "usr/libexec/mios/storage")
from ceph_mds import CephMDSOperator


def test_active_active_mds_throughput():
    """Verify aggregated metadata throughput exceeds 50,000 ops/s across 2 active ranks."""
    op = CephMDSOperator(max_mds=2)
    op.pin_subtree("/workspaces/agent-1", target_rank=0)
    op.pin_subtree("/workspaces/agent-2", target_rank=1)

    total_ops = op.simulate_mdtest_ops()
    assert total_ops > 50_000.0, f"Aggregate MDS ops/sec {total_ops} <= 50,000 SLA"


def test_standby_failover_latency():
    """Verify standby MDS transitions to active in <2.0s upon rank failure."""
    op = CephMDSOperator(max_mds=2)
    duration = op.trigger_failover(failed_rank=0)
    assert duration < 2.0, f"Failover duration {duration:.3f}s >= 2.0s SLA"
    active_count = sum(1 for r in op.ranks.values() if r.state == "active")
    assert active_count == 2, "Active ranks must recover to 2"


if __name__ == "__main__":
    test_active_active_mds_throughput()
    test_standby_failover_latency()
    print("All T-739/T-740 tests passed.")

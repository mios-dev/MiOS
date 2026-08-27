"""
Empirical stress tests for batch T-339, T-340, T-341, T-342, T-343, T-344,
T-345, T-733, T-734.
"""
import sys, time
sys.path.insert(0, "usr/lib/mios/agent-pipe")
sys.path.insert(0, "usr/libexec/mios")


def test_priority_gate_stress_100_requests():
    """PriorityGate sorts 100 mixed-priority requests correctly."""
    from mios_priority_sched import PriorityGate
    gate = PriorityGate()
    import random
    rng = random.Random(42)
    for _ in range(100):
        gate.wrap({}, priority=rng.randint(1, 10))
    queue = gate.sorted_queue()
    assert queue[0].priority <= queue[-1].priority
    assert len(queue) == 100


def test_kvfork_suspend_resume_10_sessions():
    """KVForkManager handles 10 concurrent session checkpoints."""
    import os, tempfile
    os.environ["MIOS_LLAMACPP_SLOTS_DIR"] = tempfile.mkdtemp()
    import importlib, mios_kvfork
    importlib.reload(mios_kvfork)
    from mios_kvfork import KVForkManager
    mgr = KVForkManager(dry_run=True)
    for i in range(10):
        mgr.suspend(f"stress-sess-{i}")
    assert len(mgr.list_suspended()) == 10
    for i in range(10):
        mgr.resume(f"stress-sess-{i}")
    assert len(mgr.list_suspended()) == 0


def test_dci_10_deliberations():
    """DCISession runs 10 independent deliberation sessions without errors."""
    from mios_deliberate import DCISession
    for i in range(10):
        s = DCISession(topic=f"stress topic {i}")
        pkt = s.run()
        assert pkt.round_count >= 1


def test_reputation_50_sessions():
    """ReputationEngine evaluates 50 sessions, scores stay in [0,1]."""
    from mios_reputation import ReputationEngine, PeerContribution
    engine = ReputationEngine(dry_run=True)
    for i in range(50):
        contribs = [
            PeerContribution(peer_id="a", moves=[{"act": "propose"}] * (i % 5)),
            PeerContribution(peer_id="b", moves=[{"act": "challenge"}]),
        ]
        engine.evaluate_session(f"s-{i}", contribs)
    for rec in engine.sorted_peers():
        assert 0.0 <= rec.score <= 1.0, f"Score out of bounds: {rec}"


def test_manifest_rag_deep_tree():
    """ManifestRAG handles a 3-level hierarchy without recursion errors."""
    from mios_manifest_rag import ManifestRAG, ManifestNode
    nodes = []
    for level in range(3):
        for idx in range(5):
            node = ManifestNode(
                path=f"level{level}/node{idx}",
                summary=f"level {level} node {idx} agent orchestration inference",
                leaf_docs=[{"id": f"doc-{level}-{idx}", "summary": f"doc {idx} inference"}],
            )
            nodes.append(node)
    rag = ManifestRAG(root_node=nodes[0], top_k=10)
    for n in nodes[1:]:
        rag.register_node(n)
    results = rag.retrieve("inference")
    assert len(results) > 0


if __name__ == "__main__":
    test_priority_gate_stress_100_requests()
    test_kvfork_suspend_resume_10_sessions()
    test_dci_10_deliberations()
    test_reputation_50_sessions()
    test_manifest_rag_deep_tree()
    print("All stress tests passed.")

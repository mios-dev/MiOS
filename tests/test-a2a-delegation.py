"""Tests for T-345: mios_a2a_delegation — identity-aware A2A delegation."""
import sys
sys.path.insert(0, "usr/lib/mios/agent-pipe")
from mios_a2a_delegation import (
    AgentCard, DelegationRouter, PayloadMode, DelegationFrame,
)


def _make_router():
    router = DelegationRouter()
    router.register(AgentCard(
        agent_id="agent-full",
        endpoint="http://localhost:8640",
        supported_interfaces=["text", "semantic_frame", "embedding_hints"],
        reasoning_profile="deliberate",
        cost_hint=0.8,
        capabilities={"summarize": True, "code": True},
    ))
    router.register(AgentCard(
        agent_id="agent-text-only",
        endpoint="http://localhost:8641",
        supported_interfaces=["text"],
        reasoning_profile="fast",
        cost_hint=0.3,
        capabilities={"summarize": True},
    ))
    return router


def test_negotiate_semantic_frame_when_both_support():
    """Negotiation selects semantic_frame when both peers support it."""
    router = _make_router()
    src = router.get_card("agent-full")
    tgt = router.get_card("agent-full")   # same capabilities
    mode = router.negotiate_mode(src, tgt)
    assert mode == PayloadMode.EMBEDDING_HINTS, (
        f"Expected embedding_hints (highest priority), got {mode}")


def test_negotiate_fallback_to_text():
    """Negotiation falls back to text when one peer only supports text."""
    router = _make_router()
    src = router.get_card("agent-full")
    tgt = router.get_card("agent-text-only")
    mode = router.negotiate_mode(src, tgt)
    assert mode == PayloadMode.TEXT


def test_build_frame_uses_negotiated_mode():
    """build_frame() packs structured content for capable peers."""
    router = _make_router()
    frame = router.build_frame(
        "agent-full", "agent-full",
        content_text="plain fallback",
        semantic_frame={"intent": "summarize", "key": "v"},
        embedding_hints=[0.1, 0.2, 0.3],
    )
    assert frame.mode in (PayloadMode.SEMANTIC_FRAME, PayloadMode.EMBEDDING_HINTS), (
        f"Expected structured mode, got {frame.mode}")


def test_best_peer_by_capability():
    """best_peer() returns the lowest cost_hint peer with that capability."""
    router = _make_router()
    peer = router.best_peer("summarize")
    assert peer is not None
    assert peer.agent_id == "agent-text-only"   # cost_hint=0.3 < 0.8


def test_wire_roundtrip():
    """DelegationFrame serializes and deserializes cleanly."""
    frame = DelegationFrame(
        mode=PayloadMode.SEMANTIC_FRAME,
        content={"intent": "test"},
        source_agent="a", target_agent="b",
    )
    d = frame.to_wire()
    frame2 = DelegationFrame.from_wire(d)
    assert frame2.mode == PayloadMode.SEMANTIC_FRAME
    assert frame2.content["intent"] == "test"


if __name__ == "__main__":
    test_negotiate_semantic_frame_when_both_support()
    test_negotiate_fallback_to_text()
    test_build_frame_uses_negotiated_mode()
    test_best_peer_by_capability()
    test_wire_roundtrip()
    print("All T-345 tests passed.")

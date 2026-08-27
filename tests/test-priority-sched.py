"""Tests for T-339: mios_priority_sched — engine-level priority scheduling."""
import sys, time
sys.path.insert(0, "usr/lib/mios/agent-pipe")
from mios_priority_sched import (
    PriorityGate, PriorityRequest,
    PRIORITY_FOREGROUND, PRIORITY_BACKGROUND, PRIORITY_INTERACTIVE,
)

def test_foreground_preempts_background():
    """Foreground user requests sort ahead of background batches."""
    gate = PriorityGate()
    bg  = gate.wrap({"model": "x", "messages": []}, priority=PRIORITY_BACKGROUND)
    fg  = gate.wrap({"model": "x", "messages": []}, priority=PRIORITY_FOREGROUND)

    queue = gate.sorted_queue()
    assert queue[0].priority == PRIORITY_FOREGROUND, (
        "Foreground (priority=1) must sort first")
    assert queue[1].priority == PRIORITY_BACKGROUND, (
        "Background (priority=5) must sort second")

def test_headers_injected():
    """x-priority header is set to the request priority level."""
    gate = PriorityGate()
    req  = gate.wrap({}, priority=PRIORITY_FOREGROUND)
    hdrs = gate.augment_headers(req, {"content-type": "application/json"})
    assert hdrs["x-priority"] == "1"
    assert hdrs["x-mios-priority-hint"] == "foreground"

def test_classify_user_turn_foreground():
    """User streaming turn is classified as foreground priority."""
    gate = PriorityGate()
    msgs = [{"role": "user", "content": "hello"}]
    p = gate.classify_turn(msgs, is_streaming=True)
    assert p == PRIORITY_FOREGROUND, f"Expected {PRIORITY_FOREGROUND}, got {p}"

def test_drain_order():
    """drain() returns highest-priority items first."""
    gate = PriorityGate()
    gate.wrap({}, priority=9)
    gate.wrap({}, priority=1)
    gate.wrap({}, priority=5)
    drained = gate.drain(2)
    assert drained[0].priority == 1
    assert drained[1].priority == 5
    assert len(gate._submitted) == 1

if __name__ == "__main__":
    test_foreground_preempts_background()
    test_headers_injected()
    test_classify_user_turn_foreground()
    test_drain_order()
    print("All T-339 tests passed.")

"""Tests for T-342: mios_pg_events — PostgreSQL LISTEN/NOTIFY event bus."""
import sys, asyncio
sys.path.insert(0, "usr/lib/mios/agent-pipe")
from mios_pg_events import EventBus, AgentEvent


def run(coro):
    return asyncio.run(coro)


def test_inject_and_dispatch():
    """Injected events are dispatched to subscribers within SLA."""
    bus      = EventBus(dry_run=True)
    received = []

    async def handler(evt: AgentEvent):
        received.append(evt)

    bus.subscribe(handler)
    bus.inject({"table": "tasks", "op": "INSERT", "row_id": 42})
    events = run(bus.run_once(timeout_s=0.1))
    assert len(events) == 1
    assert received[0].payload["table"] == "tasks"
    assert received[0].payload["row_id"] == 42


def test_multiple_subscribers():
    """Multiple handlers all receive each event."""
    bus = EventBus(dry_run=True)
    counts = [0, 0]

    async def h1(evt): counts[0] += 1
    async def h2(evt): counts[1] += 1

    bus.subscribe(h1)
    bus.subscribe(h2)
    bus.inject({"op": "NOTIFY"})
    run(bus.run_once())
    assert counts == [1, 1], f"Expected [1,1] got {counts}"


def test_no_events_returns_empty():
    """run_once() with no injected events returns empty list quickly."""
    bus = EventBus(dry_run=True)
    events = run(bus.run_once(timeout_s=0.05))
    assert events == []


if __name__ == "__main__":
    test_inject_and_dispatch()
    test_multiple_subscribers()
    test_no_events_returns_empty()
    print("All T-342 tests passed.")

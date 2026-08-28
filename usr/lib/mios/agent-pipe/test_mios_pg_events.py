#!/usr/bin/env python3
# AI-hint: Unit test for mios_pg_events.py
# AI-related: mios_pg_events
# AI-functions: test_agent_event, test_event_bus_inject, class TestPGEvents
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_pg_events import AgentEvent, EventBus, CHANNEL

class TestPGEvents(unittest.TestCase):
    def test_agent_event(self):
        evt = AgentEvent(channel=CHANNEL, payload={"type": "task_updated", "task_id": "T-1"})
        self.assertEqual(evt.channel, CHANNEL)
        self.assertEqual(evt.payload["type"], "task_updated")

    def test_event_bus_inject(self):
        bus = EventBus(dry_run=True)
        bus.inject({"type": "test_event"})
        self.assertEqual(bus._injected.qsize(), 1)

if __name__ == "__main__":
    unittest.main()

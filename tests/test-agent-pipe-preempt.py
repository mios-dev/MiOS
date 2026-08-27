#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI continuous batch preemption and turn scheduling.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_sched.py
"""Automated tests for WS-AI preemption counters, turn boundary slicing, and priority queues."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_pipe.scheduler.preempt import PreemptScheduler, Snapshot, Quantum

class TestAgentPipePreempt(unittest.TestCase):
    """Validates preemption slots, quantum expiration, and priority ordering."""

    def test_preempt_scheduler_slots_and_resume(self):
        sched = PreemptScheduler(max_suspended=2)
        self.assertTrue(sched.can_admit())

        slot1 = sched.acquire_slot()
        self.assertIsNotNone(slot1)
        snap1 = Snapshot("task_low", priority=1.0, position=10, partial="abc", slot=slot1)
        self.assertTrue(sched.suspend(snap1))

        slot2 = sched.acquire_slot()
        self.assertIsNotNone(slot2)
        snap2 = Snapshot("task_high", priority=10.0, position=5, partial="xyz", slot=slot2)
        self.assertTrue(sched.suspend(snap2))

        # Full slots -> cannot admit another
        self.assertFalse(sched.can_admit())

        # Resumes highest priority first
        resumed = sched.resume()
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.task_id, "task_high")

        # Now can admit again
        self.assertTrue(sched.can_admit())

    def test_quantum_expiration(self):
        q = Quantum(t0=100.0, limit_s=5.0)
        self.assertFalse(q.expired(now=104.0))
        self.assertTrue(q.expired(now=106.0))

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentPipePreempt)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

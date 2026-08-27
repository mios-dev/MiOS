#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SCHED agent-pipe token-bucket rate limiter and quotas.
# AI-related: usr/lib/mios/agent-pipe/mios_quota.py, usr/lib/mios/agent-pipe/mios_pipe/access/quota.py
"""Automated tests for WS-SCHED per-tenant rate limits, sliding windows, and budget quotas."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_pipe.access.quota import QuotaTracker, QuotaVerdict

class TestAgentPipeQuota(unittest.TestCase):
    """Validates token-bucket sliding windows, budget enforcement, and tenant isolation."""

    def test_rpm_sliding_window(self):
        qt = QuotaTracker(rpm_limit=2, window_s=60.0)
        v1 = qt.check("tenant_a", now=10.0)
        self.assertTrue(v1.allowed)

        v2 = qt.check("tenant_a", now=15.0)
        self.assertTrue(v2.allowed)

        # 3rd request in same 60s window is rejected
        v3 = qt.check("tenant_a", now=20.0)
        self.assertFalse(v3.allowed)
        self.assertIn("rate limit", v3.reason)

        # Window rolls over after 60s
        v4 = qt.check("tenant_a", now=75.0)
        self.assertTrue(v4.allowed)

    def test_cost_budget(self):
        qt = QuotaTracker(daily_budget=5.0, budget_window_s=86400.0)
        v1 = qt.check("tenant_b", now=10.0, cost=3.0)
        self.assertTrue(v1.allowed)

        # Exceeds remaining budget (3.0 + 3.0 > 5.0)
        v2 = qt.check("tenant_b", now=15.0, cost=3.0)
        self.assertFalse(v2.allowed)
        self.assertIn("budget exceeded", v2.reason)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentPipeQuota)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

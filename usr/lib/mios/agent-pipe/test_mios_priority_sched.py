#!/usr/bin/env python3
# AI-hint: Unit test for mios_priority_sched.py
# AI-related: mios_priority_sched
# AI-functions: test_priority_request, test_headers_injection, class TestPrioritySched
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_priority_sched import PriorityRequest, PRIORITY_FOREGROUND, PRIORITY_BACKGROUND

class TestPrioritySched(unittest.TestCase):
    def test_priority_request(self):
        req = PriorityRequest(payload={"prompt": "hello"}, priority=PRIORITY_FOREGROUND)
        self.assertEqual(req.priority, PRIORITY_FOREGROUND)
        self.assertGreaterEqual(req.age_s, 0.0)

    def test_headers_injection(self):
        req = PriorityRequest(payload={"prompt": "hello"}, priority=PRIORITY_FOREGROUND)
        headers = req.inject_headers({"Authorization": "Bearer key"})
        self.assertIn("x-priority", headers)
        self.assertEqual(headers["x-priority"], "1")

if __name__ == "__main__":
    unittest.main()

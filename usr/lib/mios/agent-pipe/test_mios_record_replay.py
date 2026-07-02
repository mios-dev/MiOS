#!/usr/bin/env python3
# AI-hint: Unit tests for T-040 (OBS-03 record-and-replay determinism + session hash chaining).
# Exercises the SessionChainer primitives, the httpx patching mock behavior, and stochastic seeding.
import copy
import json
import unittest
import random
import hashlib
import asyncio
import httpx

import mios_audit as A
from mios_pipe.routing.chat import _record_active, _replay_active, _replay_llm_queue, _replay_tool_queue

def _synthetic_sessions():
    return [
        {"id": "session:1", "kind": "llm_io", "owui_chat_id": "chat1", "meta": {"prompt": "p1", "completion": "c1"}},
        {"id": "session:2", "kind": "tool_io", "owui_chat_id": "chat1", "meta": {"tool": "t1", "args": {}, "output": "o1"}},
        {"id": "session:3", "kind": "llm_io", "owui_chat_id": "chat1", "meta": {"prompt": "p2", "completion": "c2"}},
    ]

def _fresh_session_chainer():
    c = A.SessionChainer()
    c.seed(0, A.GENESIS)
    return c

class TestRecordReplay(unittest.TestCase):
    def setUp(self):
        self._enable = A.CHAIN_ENABLE
        A.CHAIN_ENABLE = True
        
        # Reset context vars
        _record_active.set(False)
        _replay_active.set(False)
        _replay_llm_queue.set([])
        _replay_tool_queue.set([])

    def tearDown(self):
        A.CHAIN_ENABLE = self._enable
        _record_active.set(False)
        _replay_active.set(False)
        _replay_llm_queue.set([])
        _replay_tool_queue.set([])

    def test_session_chainer_deterministic(self):
        """Test SessionChainer generates deterministic monotonic sequences and verifies cleanly."""
        sess = _synthetic_sessions()
        c1, c2 = _fresh_session_chainer(), _fresh_session_chainer()
        s1 = [c1.stamp(dict(e)) for e in sess]
        s2 = [c2.stamp(dict(e)) for e in sess]
        
        self.assertEqual([r["chain_hash"] for r in s1], [r["chain_hash"] for r in s2])
        self.assertEqual([r["chain_seq"] for r in s1], [1, 2, 3])
        self.assertEqual(s1[0]["prev_hash"], A.GENESIS)
        
        # Verify clean chain
        res = A.verify_session_chain(s1)
        self.assertTrue(res["ok"])
        self.assertEqual(res["checked"], len(s1))
        self.assertIsNone(res["first_broken_seq"])

    def test_session_chainer_tamper_detection(self):
        """Test editing the meta in session table breaks the chain verification."""
        c = _fresh_session_chainer()
        rows = [c.stamp(dict(e)) for e in _synthetic_sessions()]
        
        # Alter meta
        tampered = copy.deepcopy(rows)
        tampered[1]["meta"]["output"] = "altered output"
        res = A.verify_session_chain(tampered)
        self.assertFalse(res["ok"])
        self.assertEqual(res["first_broken_seq"], rows[1]["chain_seq"])

    def test_stochastic_seeding(self):
        """Test seeding random with stable hash of session_id produces identical sequences."""
        sess_id = "test-session-id-12345"
        h = hashlib.md5(sess_id.encode("utf-8")).hexdigest()
        seed = int(h, 16) % (2**32)
        
        random.seed(seed)
        seq1 = [random.randint(0, 100000) for _ in range(20)]
        
        random.seed(seed)
        seq2 = [random.randint(0, 100000) for _ in range(20)]
        
        self.assertEqual(seq1, seq2)

    def test_replay_mode_httpx_interception(self):
        """Test that patched httpx.AsyncClient.post returns the mock completion when replay is active."""
        # Setup mock queue
        mock_completion = {"choices": [{"message": {"role": "assistant", "content": "mocked answer"}}]}
        _replay_llm_queue.set([
            {"kind": "llm_io", "meta": {"completion": mock_completion}}
        ])
        _replay_active.set(True)
        
        # We need a mock client to invoke
        # Patching is already active on httpx.AsyncClient.post globally
        async def run_client_call():
            async with httpx.AsyncClient() as client:
                r = await client.post("http://any-endpoint/v1/chat/completions", json={"prompt": "hello"})
                return r
                
        # asyncio.run() creates and closes a fresh loop -- get_event_loop() with
        # no running loop is an error on Python 3.12+ (the image venv may move
        # forward), so drive the coroutine loop-agnostically.
        resp = asyncio.run(run_client_call())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), mock_completion)

if __name__ == "__main__":
    unittest.main()

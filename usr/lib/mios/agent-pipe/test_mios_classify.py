# AI-hint: Stdlib unit tests for mios_classify (layer-1 micro-LLM classifiers).
#   Stubs httpx.AsyncClient + the injected verb-catalog / routing-domains / event-DB
#   helpers via configure() -- NO network, NO DB. Asserts: classify_intent empty/gate
#   -> None, parses a stubbed json verdict + fires the event row, degrades to None on
#   a non-200; _route_domain returns a validated in-enum domain, fail-opens to None
#   when disabled or on an out-of-enum label.
# AI-related: mios_classify.py, mios_config.py
"""Stdlib assert-tests for mios_classify (no network/DB)."""

import asyncio
import unittest

import mios_classify as M


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload

    def json(self):
        return self._p


class _FakeClient:
    """Async-context fake replacing httpx.AsyncClient; returns a canned response."""
    _resp = (200, {})

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        return _FakeResp(*self._resp)


def _configure(domains=None, enable=True):
    fired = []
    M.configure(
        verb_catalog={"open_app": {}, "read_file": {}},
        routing_domains=domains if domains is not None else {
            "web": {"desc": "web research", "verbs": ["web_search"]}},
        routing_enable=enable,
        db_create=lambda table, fields, **k: {"table": table, "fields": fields},
        db_post=lambda row: row,
        db_fire=lambda row: fired.append(row),
    )
    return fired


class TestClassifyIntent(unittest.TestCase):
    def setUp(self):
        _configure()
        self._real = M.httpx.AsyncClient

    def tearDown(self):
        M.httpx.AsyncClient = self._real

    def test_empty_returns_none(self):
        self.assertIsNone(asyncio.run(M.classify_intent("")))
        self.assertIsNone(asyncio.run(M.classify_intent("   ")))

    def test_parses_verdict_and_fires_event(self):
        fired = _configure()
        _FakeClient._resp = (200, {"choices": [
            {"message": {"content": '{"action":"chat","reply":"hi"}'}}]})
        M.httpx.AsyncClient = _FakeClient
        out = asyncio.run(M.classify_intent("hello there"))
        self.assertEqual(out, {"action": "chat", "reply": "hi"})
        self.assertEqual(len(fired), 1)                    # event row fired
        self.assertEqual(fired[0]["fields"]["kind"], "classify")

    def test_non_200_degrades_to_none(self):
        _FakeClient._resp = (500, {})
        M.httpx.AsyncClient = _FakeClient
        self.assertIsNone(asyncio.run(M.classify_intent("hello there")))


class TestRouteDomain(unittest.TestCase):
    def setUp(self):
        self._real = M.httpx.AsyncClient

    def tearDown(self):
        M.httpx.AsyncClient = self._real

    def test_disabled_returns_none(self):
        _configure(enable=False)
        self.assertIsNone(asyncio.run(M._route_domain("do some web research")))

    def test_in_enum_domain_returned(self):
        _configure(enable=True)
        _FakeClient._resp = (200, {"choices": [
            {"message": {"content": '{"domain":"web"}'}}]})
        M.httpx.AsyncClient = _FakeClient
        self.assertEqual(asyncio.run(M._route_domain("research X on the web")), "web")

    def test_out_of_enum_fails_open_to_none(self):
        _configure(enable=True)
        _FakeClient._resp = (200, {"choices": [
            {"message": {"content": '{"domain":"bogus"}'}}]})
        M.httpx.AsyncClient = _FakeClient
        self.assertIsNone(asyncio.run(M._route_domain("research X on the web")))


if __name__ == "__main__":
    unittest.main()

# AI-hint: Stdlib unit test for the extracted A2A peer-client consumer half (mios_a2a_client). Injects lightweight stubs via configure() -- a synthetic 3-path layered peer registry (vendor/etc/user JSON written to tmp files), a fake self-peer-url predicate, an asyncio.Lock, a by-reference _A2A_PEERS/_A2A_PEER_SKILLS/_AGENT_REGISTRY, a stub _A2A_REPUTATION recorder, a fake async HTTP client + card-fetch helper, and a worker-cache invalidator spy -- then asserts: _a2a_load_peers reads + id-dedupes + self-loop-excludes the layered registry; _a2a_probe_peer indexes a card's skills + registers the synthetic a2a:<pid> DAG agent + fires the cache invalidator; _a2a_send_message_to_peer builds the JSON-RPC message/send body shape (kind/method/params.message.parts text) against the chosen peer + records the outcome; _a2a_extract_text pulls assistant text from an A2A Task envelope (artifacts then status.message). No network, no DB, no server import.
# AI-related: ./mios_a2a_client.py, ./server.py
"""Unit tests for mios_a2a_client (A2A peer-client consumer half). Pure stdlib + stubs."""
import asyncio
import json
import os
import tempfile
import unittest

import mios_a2a_client

# The self-peer-loop guard + agent-card fetch helpers now LIVE in the module
# (moved out of server.py); capture the originals so a test that stubs them for
# the load/probe paths can be undone, leaving the real functions for the
# discovery-helper tests.
_ORIG_SELF_PEER_URL = mios_a2a_client._a2a_self_peer_url
_ORIG_FETCH_CARD = mios_a2a_client._a2a_fetch_card


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class _A2AClientBase(unittest.TestCase):
    """Restore the module-level discovery helpers after any test stubs them."""

    def tearDown(self):
        mios_a2a_client._a2a_self_peer_url = _ORIG_SELF_PEER_URL
        mios_a2a_client._a2a_fetch_card = _ORIG_FETCH_CARD


class _FakeReputation:
    def __init__(self):
        self.calls = []

    def record(self, peer_id, ok):
        self.calls.append((peer_id, bool(ok)))


class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """Captures the last POST so the test can assert the JSON-RPC body shape."""

    def __init__(self, payload):
        self._payload = payload
        self.last = None

    async def post(self, url, json=None, headers=None, timeout=None):
        self.last = {"url": url, "json": json, "headers": headers}
        return _FakeResp(self._payload)


def _base_configure(*, peers, peer_skills, registry, reputation, client,
                    fetch_card=None, paths=None, self_peer_url=None):
    cache = {"invalidated": 0}

    def _invalidate():
        cache["invalidated"] += 1

    async def _get_client():
        return client

    mios_a2a_client.configure(
        a2a_peers=peers,
        a2a_peer_skills=peer_skills,
        a2a_peers_lock=asyncio.Lock(),
        a2a_reputation=reputation,
        agent_registry=registry,
        a2a_peer_registry_paths=(paths if paths is not None else []),
        a2a_council=False,
        a2a_self_id="local-mios",
        get_client=_get_client,
        invalidate_worker_cache=_invalidate,
    )
    # The self-peer-loop guard + card-fetch helpers now LIVE in the module (no
    # longer injected); stub them directly for the load/probe paths under test.
    mios_a2a_client._a2a_self_peer_url = (self_peer_url or (lambda u: False))
    if fetch_card is not None:
        mios_a2a_client._a2a_fetch_card = fetch_card
    return cache


class TestLoadPeers(_A2AClientBase):
    def test_layered_dedupe_and_self_exclude(self):
        # Three synthetic registry files: vendor declares p1 (enabled) + a self
        # loopback peer; user overlay REPLACES p1 (disabled) + adds p2. The
        # self-peer is excluded by the injected predicate.
        files = []
        tmp = tempfile.mkdtemp()
        vendor = os.path.join(tmp, "vendor.json")
        user = os.path.join(tmp, "user.json")
        with open(vendor, "w") as f:
            json.dump({"peers": [
                {"id": "p1", "url": "http://a:8640", "enabled": True},
                {"id": "self", "url": "http://127.0.0.1:8640"},
            ]}, f)
        with open(user, "w") as f:
            json.dump({"peers": [
                {"id": "p1", "url": "http://a:8640", "enabled": False},
                {"id": "p2", "url": "http://b:8640"},
            ]}, f)
        files = [vendor, "/nonexistent/missing.json", user]

        def _is_self(u):
            return "127.0.0.1" in (u or "")

        _base_configure(peers={}, peer_skills={}, registry={},
                        reputation=_FakeReputation(), client=_FakeClient({}),
                        paths=files, self_peer_url=_is_self)
        out = mios_a2a_client._a2a_load_peers()
        by_id = {p["id"]: p for p in out}
        self.assertEqual(set(by_id), {"p1", "p2"})        # self excluded
        # user overlay REPLACED the vendor p1 -> enabled flipped to False.
        self.assertFalse(by_id["p1"]["enabled"])


class TestProbePeer(_A2AClientBase):
    def test_indexes_card_and_registers_agent(self):
        peers, peer_skills, registry = {}, {}, {}
        rep = _FakeReputation()

        async def _fetch(url, headers, timeout_s=10.0):
            return {"protocolVersion": "0.3.0", "name": "Peer One",
                    "skills": [{"id": "summarize", "name": "Summarize",
                                "tags": ["text"]}]}

        cache = _base_configure(peers=peers, peer_skills=peer_skills,
                                registry=registry, reputation=rep,
                                client=_FakeClient({}), fetch_card=_fetch)
        _run(mios_a2a_client._a2a_probe_peer(
            {"id": "p1", "url": "http://a:8640"}))
        self.assertEqual(peers["p1"]["status"], "ready")
        self.assertIn("p1", peer_skills.get("summarize", []))
        self.assertIn("a2a:p1", registry)
        self.assertEqual(registry["a2a:p1"]["lane"], "remote")
        self.assertGreaterEqual(cache["invalidated"], 1)

    def test_card_fetch_failure_marks_state(self):
        peers = {}
        rep = _FakeReputation()

        async def _fetch(url, headers, timeout_s=10.0):
            return {"error": "404 at /.well-known/agent-card.json"}

        _base_configure(peers=peers, peer_skills={}, registry={},
                        reputation=rep, client=_FakeClient({}), fetch_card=_fetch)
        _run(mios_a2a_client._a2a_probe_peer(
            {"id": "bad", "url": "http://x:8640"}))
        self.assertEqual(peers["bad"]["status"], "card-fetch-failed")


class TestSendMessageToPeer(_A2AClientBase):
    def test_jsonrpc_body_shape_and_reputation(self):
        peers = {"p1": {"id": "p1", "url": "http://a:8640", "status": "ready",
                        "headers_template": {}}}
        rep = _FakeReputation()
        client = _FakeClient({"result": {"kind": "task", "id": "t1"}})
        _base_configure(peers=peers, peer_skills={}, registry={},
                        reputation=rep, client=client)
        out = _run(mios_a2a_client._a2a_send_message_to_peer(
            "p1", "hello peer", context_id="ctx-7"))
        self.assertEqual(out, {"kind": "task", "id": "t1"})
        body = client.last["json"]
        self.assertEqual(client.last["url"], "http://a:8640/a2a")
        self.assertEqual(body["method"], "message/send")
        msg = body["params"]["message"]
        self.assertEqual(msg["kind"], "message")
        self.assertEqual(msg["contextId"], "ctx-7")
        self.assertEqual(msg["parts"][0]["text"], "hello peer")
        self.assertEqual(rep.calls, [("p1", True)])

    def test_unknown_peer(self):
        _base_configure(peers={}, peer_skills={}, registry={},
                        reputation=_FakeReputation(), client=_FakeClient({}))
        out = _run(mios_a2a_client._a2a_send_message_to_peer("ghost", "hi"))
        self.assertIn("error", out)


class TestExtractText(_A2AClientBase):
    def test_artifacts_then_status_message(self):
        env = {"artifacts": [{"parts": [{"text": "from-artifact"}]}]}
        self.assertEqual(mios_a2a_client._a2a_extract_text(env), "from-artifact")
        env2 = {"status": {"message": {"parts": [{"text": "from-status"}]}}}
        self.assertEqual(mios_a2a_client._a2a_extract_text(env2), "from-status")
        self.assertEqual(mios_a2a_client._a2a_extract_text({"error": "x"}), "")


class _FetchClient:
    """Fake async HTTP client for _a2a_fetch_card: returns a programmed
    (status, payload) per candidate URL in call order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.urls = []

    async def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        status, payload = self._responses.pop(0)
        return _FakeResp(payload, status_code=status)


class TestDiscoveryHelpers(_A2AClientBase):
    """The self-peer-loop guard / agent-card fetch / tailnet candidate helpers
    that now live in the module (moved verbatim out of server.py)."""

    def test_self_peer_url_only_excludes_loopback_on_self_port(self):
        os.environ.pop("MIOS_PORT_AGENT_PIPE", None)   # default 8640
        f = mios_a2a_client._a2a_self_peer_url
        self.assertTrue(f("http://127.0.0.1:8640"))
        self.assertTrue(f("http://localhost:8640/v1"))
        self.assertTrue(f("http://[::1]:8640"))
        # A REMOTE node on the same port is a legitimate peer, NOT self.
        self.assertFalse(f("http://10.0.0.5:8640"))
        # Loopback on a DIFFERENT port is not the self orchestrator.
        self.assertFalse(f("http://127.0.0.1:9999"))
        self.assertFalse(f(""))

    def test_self_peer_url_honours_configured_port(self):
        os.environ["MIOS_PORT_AGENT_PIPE"] = "8650"
        try:
            f = mios_a2a_client._a2a_self_peer_url
            self.assertTrue(f("http://127.0.0.1:8650"))
            self.assertFalse(f("http://127.0.0.1:8640"))
        finally:
            os.environ.pop("MIOS_PORT_AGENT_PIPE", None)

    def test_fetch_card_falls_through_candidates_and_tags_origin(self):
        # First well-known path 404s, the legacy path returns the card.
        client = _FetchClient([
            (404, {}),
            (200, {"name": "Peer", "protocolVersion": "0.3.0"}),
        ])

        async def _get_client():
            return client

        mios_a2a_client.configure(get_client=_get_client)
        card = _run(mios_a2a_client._a2a_fetch_card("http://a:8640/", {}))
        self.assertEqual(card["name"], "Peer")
        self.assertEqual(card["_fetched_from"],
                         "http://a:8640/.well-known/agent.json")
        self.assertEqual(len(client.urls), 2)

    def test_fetch_card_all_candidates_fail_returns_error(self):
        client = _FetchClient([(404, {}), (500, {}), (404, {})])

        async def _get_client():
            return client

        mios_a2a_client.configure(get_client=_get_client)
        card = _run(mios_a2a_client._a2a_fetch_card("http://a:8640", {}))
        self.assertIn("error", card)
        self.assertEqual(len(client.urls), 3)

    def test_tailnet_candidates_includes_explicit_urls_deduped(self):
        prev_urls = os.environ.get("MIOS_A2A_DISCOVER_URLS")
        prev_port = os.environ.get("MIOS_A2A_DISCOVER_PORT")
        os.environ["MIOS_A2A_DISCOVER_URLS"] = (
            "http://x:9000, http://y:9000/ , http://x:9000")
        os.environ["MIOS_A2A_DISCOVER_PORT"] = "9000"
        try:
            out = _run(mios_a2a_client._a2a_tailnet_candidates())
        finally:
            if prev_urls is None:
                os.environ.pop("MIOS_A2A_DISCOVER_URLS", None)
            else:
                os.environ["MIOS_A2A_DISCOVER_URLS"] = prev_urls
            if prev_port is None:
                os.environ.pop("MIOS_A2A_DISCOVER_PORT", None)
            else:
                os.environ["MIOS_A2A_DISCOVER_PORT"] = prev_port
        # Explicit URLs are collected first (trimmed + trailing-slash-stripped),
        # and the duplicate is removed -- they lead the candidate list regardless
        # of whether a tailscale CLI is present on the test host.
        self.assertEqual(out[:2], ["http://x:9000", "http://y:9000"])
        self.assertEqual(len(out), len(set(out)))


if __name__ == "__main__":
    unittest.main()

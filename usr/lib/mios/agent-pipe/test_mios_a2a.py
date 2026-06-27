# AI-hint: Stdlib unit test for the extracted A2A federation publish surface (mios_a2a). Injects lightweight stubs via configure() -- a fake FastAPI app, a one-agent registry, a one-verb catalog, a fake passport signer (no cryptography dependency), and a fake async HTTP client -- then asserts the AgentCard JSON shape + detached-signature presence, the Open Agent Passport + AGNTCY-OASF manifest shapes, the A2A skill-directory projection, and the JSON-RPC 2.0 method dispatch (message/send round-trip, tasks/get not-found, unknown-method error) plus the principal-metadata gate. No network, no DB, no server import.
# AI-related: ./mios_a2a.py, ./server.py
"""Unit tests for mios_a2a (A2A federation publish surface). Pure stdlib + stubs."""
import asyncio
import contextvars
import json
import unittest

import mios_a2a


class _FakeApp:
    description = "MiOS test agent"
    version = "9.9.9"


class _FakePriv:
    def sign(self, b: bytes) -> bytes:
        return b"\x01\x02\x03signature"


class _FakeResp:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "stub answer"}}]}


class _FakeClient:
    async def post(self, url, json=None, headers=None, timeout=None):
        return _FakeResp()


async def _fake_get_client():
    return _FakeClient()


_ENV_VAR = contextvars.ContextVar("client_env", default={})


def _configure():
    mios_a2a.configure(
        app=_FakeApp(),
        agent_registry={"hermes": {"role": "general", "default": True,
                                   "strengths": ["reasoning", "tools"]}},
        verb_catalog={"web_search": {"tier": "core", "desc": "search the web",
                                     "section": "web", "permission": "read"}},
        scratchpads={},
        agent_lane=lambda cfg: "gpu",
        agent_skill_tags=lambda cfg: ["reasoning", "tools"],
        match_user_cfg=lambda: ("mios", {"max_permission": "interactive"}),
        cap_skills=lambda: {},
        get_client=_fake_get_client,
        api_require_auth=True,
        client_env_var=_ENV_VAR,
        passport_load_priv=lambda: _FakePriv(),
        passport_canonical_json=lambda o: json.dumps(o, sort_keys=True,
                                                     separators=(",", ":")),
        passport_kid=lambda: "mios-test-kid",
        passport_sign=lambda table, fields: {"agent": "agent-pipe",
                                             "table": table, **fields},
        passport_verify=lambda *a, **k: (False, "stub", {}),
        passport_algo="ed25519",
        passport_enable=True,
        passport_agent_name="agent-pipe",
    )


class TestAgentCard(unittest.TestCase):
    def setUp(self):
        _configure()

    def test_card_shape_and_signature(self):
        card = mios_a2a._build_agent_card()
        self.assertEqual(card["protocolVersion"], mios_a2a.A2A_PROTOCOL_VERSION)
        self.assertEqual(card["description"], "MiOS test agent")
        self.assertEqual(card["version"], "9.9.9")
        # one [agents.*] entry -> one A2A skill, tags = the strength tokens.
        self.assertEqual(len(card["skills"]), 1)
        sk = card["skills"][0]
        self.assertEqual(sk["id"], "hermes")
        self.assertEqual(sk["tags"], ["reasoning", "tools"])
        self.assertIn("text/plain", sk["inputModes"])
        # JSONRPC transport is canonical; OpenAI advertised alongside.
        self.assertEqual(card["preferredTransport"], "JSONRPC")
        transports = {i["transport"] for i in card["additionalInterfaces"]}
        self.assertEqual(transports, {"JSONRPC", "OpenAI"})
        # securitySchemes always advertised; hard requirement when gate is on.
        self.assertIn("securitySchemes", card)
        self.assertIn("security", card)   # api_require_auth=True
        # Ed25519 detached-JWS signature present (fake signer provisioned).
        self.assertIn("signatures", card)
        self.assertEqual(card["signatures"][0]["header"]["alg"], "ed25519")
        self.assertEqual(card["signatures"][0]["header"]["kid"], "mios-test-kid")

    def test_card_unsigned_when_no_key(self):
        mios_a2a.configure(passport_load_priv=lambda: None)
        card = mios_a2a._build_agent_card()
        self.assertNotIn("signatures", card)
        _configure()   # restore the signer for other tests

    def test_passport_shape(self):
        doc = mios_a2a._build_agent_passport()
        self.assertEqual(doc["version"], mios_a2a.AGENT_PASSPORT_VERSION)
        self.assertIn("issuer", doc)
        self.assertIn("agent", doc)
        self.assertIn("authority", doc)
        self.assertIn("signature", doc)
        # no real key path -> unsigned + flagged, schema-valid.
        self.assertEqual(doc["signature"]["value"], "")
        self.assertIn("x-mios-unsigned", doc)

    def test_agntcy_manifest_shape(self):
        man = mios_a2a._build_agntcy_manifest()
        self.assertEqual(man["oasf_version"], mios_a2a.AGNTCY_OASF_SCHEMA_VERSION)
        proto_names = {p["name"] for p in man["protocols"]}
        self.assertEqual(proto_names, {"A2A", "MCP", "OpenAI"})
        self.assertEqual(len(man["features"]), 1)   # one agent skill -> one feature
        self.assertTrue(man["capabilities"]["tool_use"])


class TestSkillDirectory(unittest.TestCase):
    def setUp(self):
        _configure()

    def test_skill_directory_projection(self):
        res = asyncio.run(mios_a2a.a2a_skill_directory_logic())
        body = json.loads(res.body)
        self.assertEqual(body["object"], "mios.a2a.skill_directory")
        self.assertEqual(body["ceiling"], "interactive")
        self.assertIsInstance(body["skills"], list)


class TestJsonRpc(unittest.TestCase):
    def setUp(self):
        _configure()
        # drop principal enforcement to the default open mode for these tests.
        mios_a2a._A2A_PRINCIPAL_REQUIRE = False

    def test_unknown_method(self):
        out = asyncio.run(mios_a2a._a2a_jsonrpc_dispatch(
            {"id": 1, "method": "no/such"}))
        self.assertEqual(out["error"]["code"], -32601)

    def test_tasks_get_not_found(self):
        out = asyncio.run(mios_a2a._a2a_jsonrpc_dispatch(
            {"id": 2, "method": "tasks/get", "params": {"id": "missing"}}))
        self.assertEqual(out["error"]["code"], mios_a2a._A2A_ERR_TASK_NOT_FOUND)

    def test_tasks_get_missing_id(self):
        out = asyncio.run(mios_a2a._a2a_jsonrpc_dispatch(
            {"id": 3, "method": "tasks/get", "params": {}}))
        self.assertEqual(out["error"]["code"], -32602)

    def test_message_send_roundtrip(self):
        msg = {"id": 4, "method": "message/send",
               "params": {"message": {"role": "user",
                          "parts": [{"kind": "text", "text": "hello"}]}}}
        out = asyncio.run(mios_a2a._a2a_jsonrpc_dispatch(msg))
        task = out["result"]
        self.assertEqual(task["kind"], "task")
        self.assertEqual(task["status"]["state"], "completed")
        # the stub backend answer comes back as an artifact + agent message.
        self.assertEqual(task["artifacts"][0]["parts"][0]["text"], "stub answer")

    def test_text_from_message(self):
        txt = mios_a2a._a2a_text_from_message(
            {"parts": [{"kind": "text", "text": "a"},
                       {"type": "text", "text": "b"}]})
        self.assertEqual(txt, "a\nb")


class TestPrincipal(unittest.TestCase):
    def setUp(self):
        _configure()

    def test_metadata_none_when_disabled(self):
        mios_a2a.configure(passport_enable=False)
        # passport_enable is False -> no principal metadata attached.
        self.assertFalse(mios_a2a.PASSPORT_ENABLE)
        self.assertIsNone(
            mios_a2a._a2a_principal_metadata("text", "peer-1", "ctx-1"))
        _configure()

    def test_metadata_built_when_enabled(self):
        _ENV_VAR.set({"user_name": "corey"})
        md = mios_a2a._a2a_principal_metadata("text", "peer-1", "ctx-1")
        self.assertIsInstance(md, dict)


# -- @app route-handler logic (thin wrappers in server.py call these) --


class _FakeReq:
    """Minimal stand-in for a Starlette Request: only .json() is exercised."""
    def __init__(self, payload=None, exc=None):
        self._payload = payload
        self._exc = exc

    async def json(self):
        if self._exc is not None:
            raise self._exc
        return self._payload


class _FakeRep:
    """Reputation double: rank() is the stable identity sort the logic relies on."""
    def rank(self, ids):
        return list(ids)


async def _fake_send_to_peer(peer_id, text, context_id=None):
    return {"kind": "task", "id": "t-1", "peer_id": peer_id,
            "contextId": context_id, "echo": text}


def _configure_peer_routes():
    """Inject the consumer-side A2A deps the /v1/a2a/* route logic reads."""
    mios_a2a.configure(
        a2a_peers={"peer-1": {"status": "ready", "skills": [
            {"id": "sk1", "name": "S1", "description": "d", "tags": ["t"]}]}},
        a2a_peer_skills={"sk1": ["peer-1"]},
        a2a_peers_lock=asyncio.Lock(),
        a2a_reputation=_FakeRep(),
        a2a_send_message_to_peer=_fake_send_to_peer,
    )


class TestJsonRpcRouteLogic(unittest.TestCase):
    def setUp(self):
        _configure()
        mios_a2a._A2A_PRINCIPAL_REQUIRE = False

    def test_jsonrpc_logic_message_send(self):
        req = _FakeReq({"id": 1, "method": "message/send",
                        "params": {"message": {"role": "user", "parts": [
                            {"kind": "text", "text": "hello"}]}}})
        res = asyncio.run(mios_a2a.a2a_jsonrpc_logic(req))
        body = json.loads(res.body)
        self.assertEqual(body["result"]["status"]["state"], "completed")

    def test_jsonrpc_logic_unknown_method(self):
        req = _FakeReq({"id": 2, "method": "no/such"})
        res = asyncio.run(mios_a2a.a2a_jsonrpc_logic(req))
        self.assertEqual(json.loads(res.body)["error"]["code"], -32601)

    def test_jsonrpc_logic_batch(self):
        req = _FakeReq([{"id": 3, "method": "no/such"}])
        res = asyncio.run(mios_a2a.a2a_jsonrpc_logic(req))
        body = json.loads(res.body)
        self.assertIsInstance(body, list)
        self.assertEqual(body[0]["error"]["code"], -32601)

    def test_jsonrpc_logic_parse_error(self):
        res = asyncio.run(mios_a2a.a2a_jsonrpc_logic(_FakeReq(exc=ValueError("boom"))))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json.loads(res.body)["error"]["code"], -32700)


class TestPeerRouteLogic(unittest.TestCase):
    def setUp(self):
        _configure()
        _configure_peer_routes()

    def test_skills_list_logic(self):
        res = asyncio.run(mios_a2a.a2a_skills_list_logic())
        body = json.loads(res.body)
        self.assertEqual(body["object"], "mios.a2a.skills")
        self.assertEqual(body["skills"][0]["id"], "sk1")
        self.assertEqual(body["skills"][0]["peers"][0]["peer_id"], "peer-1")

    def test_dispatch_logic_by_skill(self):
        res = asyncio.run(mios_a2a.a2a_dispatch_logic(
            _FakeReq({"skill": "sk1", "text": "hi"})))
        body = json.loads(res.body)
        self.assertEqual(body["peer_id"], "peer-1")
        self.assertEqual(body["echo"], "hi")

    def test_dispatch_logic_missing_text(self):
        res = asyncio.run(mios_a2a.a2a_dispatch_logic(
            _FakeReq({"peer_id": "peer-1"})))
        self.assertEqual(res.status_code, 400)
        self.assertIn("missing", json.loads(res.body)["error"])

    def test_dispatch_logic_no_peer(self):
        res = asyncio.run(mios_a2a.a2a_dispatch_logic(
            _FakeReq({"skill": "nope", "text": "hi"})))
        self.assertEqual(res.status_code, 404)


class TestPassportRouteLogic(unittest.TestCase):
    def setUp(self):
        _configure()
        # passport_verify returns the 2-tuple (ok, reason) shape the /passport/verify
        # body unpacks (distinct from the 3-tuple principal verify_fn stub above).
        mios_a2a.configure(
            passport_verify=lambda env, payload=None: (True, "ok"),
            passport_load_public=lambda agent: (
                object() if agent == "agent-pipe" else None),
        )

    def test_passport_verify_logic_ok(self):
        res = asyncio.run(mios_a2a.passport_verify_logic(
            _FakeReq({"envelope": {"agent": "a", "kid": "k", "alg": "ed25519"}})))
        body = json.loads(res.body)
        self.assertTrue(body["ok"])
        self.assertEqual(body["reason"], "ok")
        self.assertEqual(body["agent"], "a")

    def test_passport_verify_logic_bad_json(self):
        res = asyncio.run(mios_a2a.passport_verify_logic(_FakeReq(exc=ValueError("x"))))
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid JSON", json.loads(res.body)["error"])

    def test_passport_verify_logic_no_envelope(self):
        res = asyncio.run(mios_a2a.passport_verify_logic(_FakeReq({"foo": 1})))
        self.assertEqual(res.status_code, 400)
        self.assertIn("envelope", json.loads(res.body)["error"])

    def test_passport_public_key_logic_missing(self):
        # The not-found path returns BEFORE the cryptography PEM-serialization
        # import, so it asserts offline (no cryptography dependency).
        res = asyncio.run(mios_a2a.passport_public_key_logic("nobody"))
        self.assertEqual(res.status_code, 404)
        self.assertIn("no public key", json.loads(res.body)["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_pdp (WS-A9 PDP capability gate).
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_pdp (WS-A9)."""

import sys

import mios_pdp as pdp

TIERS = ["read", "write", "interactive"]
_fails = 0

def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))

def t_rank():
    check("rank: read=0", pdp.permission_rank("read", TIERS) == 0)
    check("rank: write=1", pdp.permission_rank("write", TIERS) == 1)
    check("rank: interactive=2", pdp.permission_rank("interactive", TIERS) == 2)
    check("rank: unknown tier ranks ABOVE top (fail-closed)",
          pdp.permission_rank("nuke", TIERS) == 3)
    check("rank: case/space-insensitive", pdp.permission_rank("  WRITE ", TIERS) == 1)

def t_ceiling():
    check("ceiling: empty -> None (no ceiling)", pdp.resolve_ceiling("", TIERS) is None)
    check("ceiling: absent -> None", pdp.resolve_ceiling(None, TIERS) is None)
    check("ceiling: known tier -> its rank", pdp.resolve_ceiling("write", TIERS) == 1)
    check("ceiling: UNKNOWN tier -> 0 (FAIL CLOSED, not None)",
          pdp.resolve_ceiling("supervisor", TIERS) == 0)
    check("ceiling: typo'd tier -> 0 (fail closed)", pdp.resolve_ceiling("writ", TIERS) == 0)

def _d(name, *, in_catalog=True, verb_perm="read", denied=(), allowed=(), ceiling=None):
    return pdp.decide(name, in_catalog=in_catalog, verb_perm=verb_perm,
                      denied=denied, allowed=allowed,
                      ceiling_rank=ceiling, tiers=TIERS)

def t_decide():
    check("decide: empty policy allows", _d("open_app").allow)
    check("decide: denied verb -> deny", not _d("open_app", denied=["open_app"]).allow)
    check("decide: denied rule named", _d("x", denied=["x"]).rule == "denied_verbs")
    check("decide: allowed-list excludes others",
          not _d("open_app", allowed=["web_search"]).allow)
    check("decide: allowed-list includes self",
          _d("web_search", allowed=["web_search"]).allow)
    ceil_read = pdp.resolve_ceiling("read", TIERS)
    check("decide: ceiling read drops write verb",
          not _d("pc_type", verb_perm="write", ceiling=ceil_read).allow)
    check("decide: ceiling read keeps read verb",
          _d("list_windows", verb_perm="read", ceiling=ceil_read).allow)
    check("decide: ceiling rule named",
          _d("pc_type", verb_perm="write", ceiling=ceil_read).rule == "max_permission")
    bad_ceil = pdp.resolve_ceiling("typo", TIERS)
    check("decide: fail-closed ceiling drops write verb",
          not _d("pc_type", verb_perm="write", ceiling=bad_ceil).allow)
    check("decide: fail-closed ceiling keeps read verb",
          _d("list_windows", verb_perm="read", ceiling=bad_ceil).allow)

def t_non_verb():
    check("non-verb: passes allowed-list (not a verb)",
          _d("some_mcp_tool", in_catalog=False, allowed=["web_search"]).allow)
    check("non-verb: passes ceiling (not a verb)",
          _d("some_skill", in_catalog=False, verb_perm="write",
             ceiling=pdp.resolve_ceiling("read", TIERS)).allow)
    check("non-verb: denied STILL applies",
          not _d("evil_tool", in_catalog=False, denied=["evil_tool"]).allow)
    check("non-verb: rule = non_verb when allowed",
          _d("t", in_catalog=False).rule == "non_verb")

def main() -> int:
    t_rank()
    t_ceiling()
    t_decide()
    t_non_verb()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0



# ==============================================================================
# Consolidated from test_mios_auth.py (T-1092)
# ==============================================================================
# AI-hint: Placeholder test for mios_auth.py.
def test_stub():
    pass

def _run_extra_auth():
    import os
    _saved_env = dict(os.environ)
    try:
        return 0
    except SystemExit as _e:
        return _e.code if _e.code is not None else 0
    finally:
        os.environ.clear()
        os.environ.update(_saved_env)



# ==============================================================================
# Consolidated from test_mios_authn.py (T-1092)
# ==============================================================================
# AI-hint: Unit tests for mios_pipe.access.authn.
"""Unit tests for authentication and caller key management."""

import json
import os
import tempfile
import unittest

from mios_pipe.access.authn import (
    _bind_host,
    _check_inbound_principal,
    _load_backend_key,
    _probe_auth_headers,
    configure as configure_authn,
)

class TestAuthn(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.caller_keys_file = os.path.join(self.tmp_dir.name, "caller-keys.json")

        keys_data = {
            "keys": {
                "secret_token_123": {"principal": "worker_agent", "scope": "read"},
            }
        }
        with open(self.caller_keys_file, "w", encoding="utf-8") as fh:
            json.dump(keys_data, fh)

        configure_authn(
            backend_key="backend_secret_xyz",
            ingress_key="ingress_secret_999",
            api_require_auth=True,
            caller_keys_path=self.caller_keys_file,
            auth_hostports={"127.0.0.1:8000"},
            agent_auth_by_hostport={"remote:8000": "Bearer remote_tok"},
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_check_inbound_principal_shared_and_caller(self):
        op = _check_inbound_principal("backend_secret_xyz")
        self.assertIsNotNone(op)
        self.assertEqual(op["principal"], "operator")

        ck = _check_inbound_principal("secret_token_123")
        self.assertIsNotNone(ck)
        self.assertEqual(ck["principal"], "worker_agent")

        un = _check_inbound_principal("invalid_token_999")
        self.assertIsNone(un)

    def test_probe_auth_headers(self):
        hdrs = _probe_auth_headers("http://127.0.0.1:8000/v1/models")
        self.assertEqual(hdrs.get("Authorization"), "Bearer backend_secret_xyz")

    def test_bind_host(self):
        self.assertEqual(_bind_host(require_auth=False), "127.0.0.1")
        self.assertEqual(_bind_host(require_auth=True), "0.0.0.0")
        self.assertEqual(_bind_host(require_auth=False, override="10.0.0.5"), "10.0.0.5")


def _run_extra_authn():
    import os
    _saved_env = dict(os.environ)
    try:
        import unittest
        suite = unittest.TestSuite()
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestAuthn))
        res = unittest.TextTestRunner().run(suite)
        return 0 if res.wasSuccessful() else 1
    except SystemExit as _e:
        return _e.code if _e.code is not None else 0
    finally:
        os.environ.clear()
        os.environ.update(_saved_env)



def _run_all_folded_pdp_suites():
    rc = _run_extra_auth()
    if rc not in (None, 0):
        import sys
        sys.exit(f"Folded test suite failed: exit code {rc}")
    rc = _run_extra_authn()
    if rc not in (None, 0):
        import sys
        sys.exit(f"Folded test suite failed: exit code {rc}")

if __name__ == "__main__":
    _rc_main = main()
    _run_all_folded_pdp_suites()
    sys.exit(_rc_main)

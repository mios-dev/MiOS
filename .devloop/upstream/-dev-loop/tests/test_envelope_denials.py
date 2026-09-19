#!/usr/bin/env python3
"""A headless run that did nothing must never read as a success (stdlib only).

SKILL.md §10: "Headless 'green' can hide denials. A headless run whose tool calls were
*denied* can still exit 0 with is_error: false; only the envelope's permission_denials
reveals it." This suite pins the two places that promise to catch it:

  * normalize_report()  -- the lane path
  * `adapters.py denials`  -- the seam a host uses when it runs a harness itself

The fixture is the shape observed live from agy 1.2.6: status SUCCESS, an EMPTY
response, one turn, denied_actions naming the tool -- behind the stderr notice agy
prints, because a caller that merges the streams is the case that used to slip through.

Run directly:  python3 tests/test_envelope_denials.py
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADAPTERS = REPO / "skills" / "dev-loop" / "scripts" / "adapters.py"

# The live shape, verbatim in structure: SUCCESS + empty response + denied_actions.
DENIED = {
    "conversation_id": "00000000-0000-0000-0000-000000000000",
    "status": "SUCCESS",
    "response": "",
    "duration_seconds": 9.02,
    "num_turns": 1,
    "usage": {"total_tokens": 16472},
    "denied_actions": [{"action": "read_file", "display_name": "ViewFile"}],
}
NOTICE = ('jetski: no output produced — a tool required the "read_file" permission that '
          "headless mode cannot prompt for, so it was auto-denied.\n")
CLEAN = {"conversation_id": "x", "status": "SUCCESS", "response": "merged 4 lanes",
         "duration_seconds": 812, "num_turns": 37, "usage": {"total_tokens": 99}}


def load_adapters():
    spec = importlib.util.spec_from_file_location("adapters_under_test", ADAPTERS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_denials(text):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(text)
        path = fh.name
    try:
        cp = subprocess.run([sys.executable, str(ADAPTERS), "denials", path],
                            capture_output=True, text=True)
        return cp.returncode, cp.stdout + cp.stderr
    finally:
        Path(path).unlink(missing_ok=True)


class LanePath(unittest.TestCase):
    """normalize_report must downgrade a denied run even through a merged stream."""

    @classmethod
    def setUpClass(cls):
        cls.ad = load_adapters()

    def normalize(self, stdout):
        return self.ad.normalize_report({"id": "t", "objective": "o"}, "antigravity",
                                        stdout, 0, False, 1)

    def test_denial_seen_behind_a_stderr_notice(self):
        """The regression: a bare json.loads() raises here and skips the check."""
        rep = self.normalize(NOTICE + json.dumps(DENIED))
        self.assertEqual(rep["status"], "partial")
        self.assertTrue(any("denied_actions" in u for u in rep["unverified"]),
                        f"denial not reported: {rep['unverified']}")

    def test_denial_seen_in_a_bare_envelope(self):
        rep = self.normalize(json.dumps(DENIED))
        self.assertEqual(rep["status"], "partial")
        self.assertTrue(any("denied_actions" in u for u in rep["unverified"]))

    def test_claude_code_permission_denials_also_downgrade(self):
        env = {"result": "some of it", "num_turns": 9,
               "permission_denials": [{"tool_name": "Bash"}, {"tool_name": "Write"}]}
        rep = self.normalize(json.dumps(env))
        self.assertTrue(any("permission_denials" in u for u in rep["unverified"]))

    def test_clean_envelope_is_not_downgraded(self):
        """Positive control: the fix must not fire on a healthy run."""
        rep = self.normalize(NOTICE.replace("no output produced", "unrelated warning")
                             + json.dumps(CLEAN))
        self.assertFalse(any("denied" in u for u in rep["unverified"]),
                         f"false positive on a clean envelope: {rep['unverified']}")


class HostSeam(unittest.TestCase):
    """`adapters.py denials` is what a host that runs a harness itself calls."""

    def test_denied_run_exits_nonzero_and_names_the_tool(self):
        rc, out = run_denials(NOTICE + json.dumps(DENIED))
        self.assertNotEqual(rc, 0)
        self.assertIn("read_file", out)

    def test_empty_response_alone_is_a_failure(self):
        """SUCCESS over one turn with nothing said is not a success."""
        env = dict(DENIED); env.pop("denied_actions")
        rc, out = run_denials(json.dumps(env))
        self.assertNotEqual(rc, 0)
        self.assertIn("EMPTY", out)

    def test_missing_envelope_is_a_failure_not_a_pass(self):
        """No envelope means we cannot tell whether anything ran -- never a pass."""
        rc, out = run_denials("segfault\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("no harness result envelope", out)

    def test_clean_envelope_passes(self):
        rc, out = run_denials(json.dumps(CLEAN))
        self.assertEqual(rc, 0, out)
        self.assertIn("clean", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

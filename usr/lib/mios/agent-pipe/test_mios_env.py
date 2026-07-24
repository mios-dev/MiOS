# AI-hint: Unit test for empty MIOS_* env contract (AGY-98).
# Asserts that every agent-pipe module imports cleanly even when os.environ is populated
# with empty MIOS_* variables.
# ============================================================================
# usr/lib/mios/agent-pipe/test_mios_env.py
# ============================================================================

import os
import sys
import unittest

# Ensure usr/lib/mios and usr/lib/mios/agent-pipe are in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
USR_LIB = os.path.abspath(os.path.join(BASE_DIR, ".."))
if USR_LIB not in sys.path:
    sys.path.insert(0, USR_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mios_env import strip_empty_mios_env


class TestMiosEnvContract(unittest.TestCase):
    def test_strip_empty_mios_env(self):
        test_env = {
            "MIOS_FIXTURE_FOO": "",
            "MIOS_FIXTURE_BAR": "123",
            "OTHER_VAR": "",
        }
        stripped = strip_empty_mios_env(test_env)
        self.assertNotIn("MIOS_FIXTURE_FOO", stripped)
        self.assertIn("MIOS_FIXTURE_BAR", stripped)
        self.assertIn("OTHER_VAR", stripped)

    def test_import_agent_pipe_with_empty_env(self):
        # Populate env with dummy empty MIOS_* variables
        sample_keys = [
            "MIOS_FIXTURE_PORT_AGENT_PIPE",
            "MIOS_FIXTURE_PORT_HTTP",
            "MIOS_FIXTURE_TIMEOUT",
            "MIOS_FIXTURE_MAX_WORKERS",
            "MIOS_FIXTURE_ENABLE_FEATURE",
        ]
        for k in sample_keys:
            os.environ[k] = ""

        # Import mios_pipe and ensure strip_empty_mios_env handles them
        import mios_pipe
        import mios_pipe.kernel.config

        for k in sample_keys:
            self.assertNotIn(k, os.environ)


if __name__ == "__main__":
    unittest.main()

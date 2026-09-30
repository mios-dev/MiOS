#!/usr/bin/env python3
# AI-hint: Thin entrypoint shim -- the chat-promotion smoke corpus now lives in the canonical consolidated suite tests/test-refine-guards.py ...
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Entrypoint shim: delegates to the canonical consolidated suite.

This filename stays because it is an externally referenced entrypoint
(registered in ``[ci.tiers] unit`` in usr/share/mios/mios.toml and mirrored in
usr/share/mios/ai/v1/metadata.json), but ALL refine guard coverage --
including this file's former live chat-promotion smoke cases
("mios-open-url https://www.wikipedia.org", "https://example.com",
"git status") -- now lives once, losslessly, in
``tests/test-refine-guards.py``, which exercises the REAL production
``refine_intent`` (imported from ``usr/lib/mios/agent-pipe/mios_refine.py``)
rather than an inline copy.

Running this shim == running the canonical suite (offline deterministic
guards verified; live integration tests SKIP explicitly unless
``MIOS_REFINE_LIVE_ENDPOINT`` is set).
"""
from __future__ import annotations
import importlib.util
import os
import sys

import _agentpipe_path  # noqa: F401  keeps the suite on the repo agent-pipe
os.environ.setdefault("MIOS_TOML", "/usr/share/mios/mios.toml")

_CANONICAL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "test-refine-guards.py")


def _run_canonical() -> int:
    spec = importlib.util.spec_from_file_location(
        "test_refine_guards_canonical", _CANONICAL)
    if spec is None or spec.loader is None:
        print(f"FAIL: cannot load canonical suite at {_CANONICAL}")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._run_all_standalone()


if __name__ == "__main__":
    print("[refine-guard] delegating to canonical suite "
          "tests/test-refine-guards.py")
    sys.exit(_run_canonical())

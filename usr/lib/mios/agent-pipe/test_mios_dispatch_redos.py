#!/usr/bin/env python3
# AI-hint: Regression test for the ReDoS in dispatch_cmd's podman-exec shell-stripper -- pins a wall-clock bound on a pathological input, not a pattern string.
# AI-related: usr/lib/mios/agent-pipe/mios_pipe/routing/dispatch_cmd.py
"""Regression: the podman-exec stripper must not backtrack exponentially.

The flag-repetition group allowed a flag's ARGUMENT to start with '-', so
"-a -b" had two legal parses and the group backtracked exponentially (~1.64^n
measured) on model-controlled script text. The bound pinned here is wall-clock
on a pathological input rather than an assertion about the pattern string,
because the defect is behavioural; flags-with-arguments are pinned too, since
that is what the narrowed character class could plausibly break.
"""

import os
import re
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "mios_pipe/routing/dispatch_cmd.py")


def _shell_strip_pattern():
    """The live pattern, read from the shipped source.

    Extracted rather than imported: importing dispatch_cmd pulls the whole
    agent-pipe dependency tree, and this defect is in one literal.
    """
    with open(SRC, encoding="utf-8") as fh:
        body = fh.read()
    m = re.search(r"r'(\\b\(podman\\s\+exec.*?)',\n", body, re.S)
    if not m:
        raise AssertionError("the podman-exec stripper pattern was not found -- "
                             "renamed or restructured? Update this test.")
    return m.group(1)


class TestNoExponentialBacktracking(unittest.TestCase):
    def setUp(self):
        self.rx = re.compile(_shell_strip_pattern(),
                             re.IGNORECASE | re.MULTILINE)

    def test_a_pathological_input_stays_fast(self):
        # Pre-fix this took ~1.9s at n=32 and grew ~2.7x per +2. n=2000 would
        # not have finished in the lifetime of the process.
        s = "podman exec " + "-- " * 2000 + "!"
        t0 = time.time()
        self.rx.search(s)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 1.0,
                        "shell-stripper took %.3fs on a 2000-repetition input -- "
                        "the backtracking regression is back" % elapsed)

    def test_growth_is_not_exponential(self):
        # Doubling the input must not square the time. A generous factor keeps
        # this stable on a loaded runner while still catching 1.64^n.
        def t(n):
            s = "podman exec " + "-- " * n + "!"
            t0 = time.time()
            self.rx.search(s)
            return time.time() - t0

        small, big = t(200), t(400)
        self.assertLess(big, max(small * 8, 0.5),
                        "doubling the input multiplied the time by %.1f" %
                        (big / small if small else 0))


class TestBehaviourUnchanged(unittest.TestCase):
    def setUp(self):
        self.rx = re.compile(_shell_strip_pattern(),
                             re.IGNORECASE | re.MULTILINE)

    def _strip(self, s):
        return self.rx.sub(r'\1 true', s)

    def test_a_bare_shell_is_neutralised(self):
        self.assertEqual(self._strip("podman exec -it mios-pgvector bash"),
                         "podman exec -it mios-pgvector true")
        self.assertEqual(self._strip("podman exec mios-forge sh"),
                         "podman exec mios-forge true")

    def test_flags_WITH_arguments_still_strip(self):
        # The fix narrowed the argument class to [^-\s]\S*, so these are the
        # cases most likely to break if it were narrowed wrongly.
        for src, want in (
            ("podman exec -i --user 1000 mios-ai /bin/bash",
             "podman exec -i --user 1000 mios-ai true"),
            ("podman exec -e FOO=bar mios-x zsh -l",
             "podman exec -e FOO=bar mios-x true"),
            ("podman exec --workdir /srv mios-y /bin/sh",
             "podman exec --workdir /srv mios-y true"),
        ):
            self.assertEqual(self._strip(src), want, src)

    def test_a_real_command_is_left_alone(self):
        for s in ("echo hello",
                  "podman exec -it mios-z bash -c 'ls'"):
            self.assertEqual(self._strip(s), s, s)


if __name__ == "__main__":
    unittest.main()

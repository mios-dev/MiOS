#!/usr/bin/env python3
"""Every gate-diffed generator's --check must agree with its write mode.

The defect this exists to catch: tools/generate-bib-configs.py --check
compared only the VALUE it projects, via a tolerant regex, while write mode
ALSO normalised surrounding whitespace. config/artifacts/iso.toml carried
aligned padding, so --check printed PASS on a file the generator rewrote on
sight. The drift gate calls --check, so it reported in-sync while the
committed artifact did not match its own generator.

A check that does not compare what the writer produces cannot detect the
drift the writer creates. This test asserts the invariant directly: run each
generator for real, and if it changed a tracked file, --check must have
refused to call the tree clean.

The generator -> target pairs are read from the gate itself rather than
listed here, so a generator added to the gate is covered without editing
this file.
"""
import os
import re
import subprocess
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GATE = os.path.join(_ROOT, "automation", "98-drift-checks.sh")


def _projection_pairs():
    """(generator, [targets]) as declared by the gate's evidence emitter."""
    with open(_GATE, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    pairs = []
    for line in text.splitlines():
        if "_emit_projection_evidence " not in line:
            continue
        args = re.findall(r'"([^"]+)"', line)
        if len(args) >= 2 and args[0].endswith(".py"):
            pairs.append((args[0], args[1:]))
    return pairs


class GeneratorCheckAgreesWithWrite(unittest.TestCase):
    def test_the_gate_declares_projection_pairs(self):
        # A zero-length list would make every other test here vacuous.
        self.assertTrue(_projection_pairs(),
                        "no _emit_projection_evidence pairs found in the gate; "
                        "this suite would silently test nothing")

    def test_check_mode_refuses_a_tree_write_mode_would_change(self):
        env = dict(os.environ, MIOS_DRIFT_ROOT=_ROOT)
        for gen, targets in _projection_pairs():
            gen_abs = os.path.join(_ROOT, gen)
            if not os.path.isfile(gen_abs):
                continue

            before = {}
            for rel in targets:
                p = os.path.join(_ROOT, rel)
                if os.path.isfile(p):
                    with open(p, "rb") as fh:
                        before[rel] = fh.read()

            try:
                subprocess.run([sys.executable, gen_abs], cwd=_ROOT, env=env,
                               capture_output=True, text=True)
                changed = []
                for rel, original in before.items():
                    p = os.path.join(_ROOT, rel)
                    with open(p, "rb") as fh:
                        now = fh.read()
                    if now != original:
                        changed.append(rel)

                chk = subprocess.run([sys.executable, gen_abs, "--check"],
                                     cwd=_ROOT, env=env,
                                     capture_output=True, text=True)
                if changed:
                    self.assertNotEqual(
                        0, chk.returncode,
                        "%s --check reported the tree in sync, but running it "
                        "rewrote %s. check mode must compare what write mode "
                        "produces." % (gen, ", ".join(changed)))
            finally:
                # Never leave the caller's tree dirty, even on failure.
                for rel, original in before.items():
                    with open(os.path.join(_ROOT, rel), "wb") as f:
                        f.write(original)

    def test_generated_artifacts_are_lf_on_every_host(self):
        # Python text mode translates newlines to the host separator, so a
        # generator without an explicit newline="\n" emits CRLF on Windows and
        # LF on Linux. The gate diffs generated against committed, which made
        # these checks fire on who ran them rather than on real drift.
        cr = chr(13).encode()
        for gen, targets in _projection_pairs():
            for rel in targets:
                p = os.path.join(_ROOT, rel)
                if not os.path.isfile(p):
                    continue
                with open(p, "rb") as fh:
                    body = fh.read()
                self.assertNotIn(
                    cr, body,
                    "%s (written by %s) contains CR; pin the write with "
                    'newline="\n"' % (rel, gen))


if __name__ == "__main__":
    unittest.main(verbosity=2)

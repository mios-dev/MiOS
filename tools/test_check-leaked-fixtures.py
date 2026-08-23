#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-leaked-fixtures.py; proves the scan catches an injected fixture and a backup file.
# AI-related: tools/check-leaked-fixtures.py, tests/drift-gate-negatives.sh
"""The scan found five real leaks on its first run; these cases keep it able to.

Each test plants the shape in a throwaway git repository and asserts the checker
goes red, because a leak detector that cannot detect is worse than none: it
stops anyone looking.
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MARKER = "neg" + "test"


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_leaked_fixtures", os.path.join(_HERE, "check-leaked-fixtures.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _repo(files):
    """A throwaway git repo tracking `files` (name -> content), with a ceiling of 0."""
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=False,
                   capture_output=True)
    os.makedirs(os.path.join(d, "usr", "share", "mios"), exist_ok=True)
    with open(os.path.join(d, "usr/share/mios/mios.toml"), "w",
              encoding="utf-8") as fh:
        fh.write("[tests]\nmax_leaked_fixtures = 0\n")
    for name, body in files.items():
        full = os.path.join(d, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)
    subprocess.run(["git", "-C", d, "add", "-A"], check=False,
                   capture_output=True)
    return d


def _run(root):
    old = os.environ.get("MIOS_DRIFT_ROOT")
    os.environ["MIOS_DRIFT_ROOT"] = root
    try:
        return MOD.main()
    finally:
        if old is None:
            os.environ.pop("MIOS_DRIFT_ROOT", None)
        else:
            os.environ["MIOS_DRIFT_ROOT"] = old


class TestLeakedFixtures(unittest.TestCase):
    def test_a_clean_tree_passes(self):
        self.assertEqual(0, _run(_repo({"a.sh": "echo hello\n"})))

    def test_an_injected_marker_fails(self):
        body = "CREATE TABLE mios_%s_orphan (id int);\n" % _MARKER
        self.assertNotEqual(0, _run(_repo({"schema.sql": body})))

    def test_a_tracked_backup_file_fails(self):
        self.assertNotEqual(0, _run(_repo({"thing.ps1.negbak": "x\n"})))

    def test_a_hidden_file_fails(self):
        """A test that hides a file renames it aside; one had reached HEAD."""
        self.assertNotEqual(0, _run(_repo({"ch01.md.neg-hidden": "x\n"})))

    def test_an_absent_ceiling_fails(self):
        d = _repo({"a.sh": "true\n"})
        os.remove(os.path.join(d, "usr/share/mios/mios.toml"))
        self.assertNotEqual(0, _run(d))

    def test_the_shipped_tree_is_clean(self):
        self.assertEqual(0, _run(_ROOT))


if __name__ == "__main__":
    unittest.main(verbosity=1)

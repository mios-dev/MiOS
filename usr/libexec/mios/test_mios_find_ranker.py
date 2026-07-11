#!/usr/bin/env python3
# AI-hint: Unit-proves the mios-find launch-disambiguation ranker reads its
# scoring SSOT (tier ordering, category-priority weights, fuzzy bounds) from
# mios.toml -- defaults preserve historical behaviour, a non-default config
# flips the winner. Pure in-process exec of the script's embedded ranker; no
# bash, no mios-apps subprocess.
# AI-related: /usr/libexec/mios/mios-find, /usr/share/mios/mios.toml
"""Tests for the mios-find ranker SSOT (mios.toml [mios-find.ranker] +
[mios-find.category_priority]).

The ranker lives in an embedded python heredoc inside the bash script
``mios-find``. We extract that block, stub the ``mios-apps --json`` inventory
call, point ``MIOS_TOML`` at a temp config, exec it in-process, and assert the
chosen launch command. Defaults must reproduce the historical in-code ranking;
a non-default config must change it -- proving the weights are read from SSOT,
not baked.
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MIOS_FIND = os.path.join(_HERE, "mios-find")
# mios-find invokes the ranker heredoc as `python3 - "<.../lib/mios>" "$QUERY"`,
# so argv[1] is the shared-resolver lib dir and argv[2] is the query. Mirror that
# 3-arg contract here (was the old 2-arg [prog, query] -> ModuleNotFoundError /
# IndexError -> the libexec test gate die'd the whole OCI build).
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "lib", "mios"))


def _extract_ranker_source():
    """Pull the fast-path-B python heredoc (the block that defines rank())."""
    with open(_MIOS_FIND, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    blocks = []
    body = None
    for line in lines:
        if body is None:
            if line.endswith("<<'PYEOF'"):
                body = []
            continue
        if line.strip() == "PYEOF":
            blocks.append("\n".join(body))
            body = None
            continue
        body.append(line)
    for b in blocks:
        if "def rank(" in b:
            return b
    raise AssertionError("could not locate the ranker python block in mios-find")


_RANKER_SRC = _extract_ranker_source()


def run_ranker(query, entries, toml_text):
    """Exec the extracted ranker with a stubbed inventory + a temp MIOS_TOML.

    entries: list of dicts (mios-apps JSONL shape: name/category/launch/...).
    Returns (winner_launch_or_None, exit_code, stderr_text).
    """
    jsonl = "\n".join(__import__("json").dumps(e) for e in entries)

    fake_proc = types.SimpleNamespace(stdout=jsonl, stderr="", returncode=0)

    def fake_run(*_a, **_kw):
        return fake_proc

    fd, toml_path = tempfile.mkstemp(suffix=".toml")
    os.close(fd)
    with open(toml_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(toml_text))

    orig_run = subprocess.run
    orig_argv = sys.argv
    # mios-find's ranker reads the shared mios_toml resolver, which layers
    # VENDOR<HOST<USER from MIOS_VENDOR_TOML/MIOS_HOST_TOML/MIOS_USER_TOML (NOT
    # the old MIOS_TOML). Point the vendor layer at the fixture and isolate
    # host/user at nonexistent paths so ONLY the fixture is merged.
    _env_keys = ("MIOS_VENDOR_TOML", "MIOS_HOST_TOML", "MIOS_USER_TOML")
    orig_env = {k: os.environ.get(k) for k in _env_keys}
    _absent = os.path.join(tempfile.gettempdir(), "mios-find-test-absent-layer.toml")
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        subprocess.run = fake_run
        sys.argv = ["mios-find", _LIB, query]
        os.environ["MIOS_VENDOR_TOML"] = toml_path
        os.environ["MIOS_HOST_TOML"] = _absent
        os.environ["MIOS_USER_TOML"] = _absent
        ns = {"__name__": "__mios_find_ranker__"}
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                exec(compile(_RANKER_SRC, "<mios-find-ranker>", "exec"), ns)
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else (0 if not e.code else 1)
    finally:
        subprocess.run = orig_run
        sys.argv = orig_argv
        for k, v in orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        os.unlink(toml_path)

    stdout_lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
    winner = stdout_lines[0] if (code == 0 and stdout_lines) else None
    return winner, code, err.getvalue()


# Config snippets ---------------------------------------------------------
# A toml with NO ranker sections -> loader degrades to the baked defaults.
_NO_RANKER_CFG = """
    [some-other-section]
    x = 1
"""


class CategoryPriorityFromSSOT(unittest.TestCase):
    # Two entries tie at the strongest tier (name_exact); the category-priority
    # weight is the only tiebreaker, so flipping it in config flips the winner.
    ENTRIES = [
        {"name": "foo", "category": "mios-shim", "launch": "SHIM"},
        {"name": "foo", "category": "windows-app", "launch": "APP"},
    ]

    def test_default_category_priority_picks_real_app(self):
        # Historical default: windows-app (1) outranks mios-shim (6) -> APP.
        winner, code, _ = run_ranker("foo", self.ENTRIES, _NO_RANKER_CFG)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "APP")

    def test_override_category_priority_flips_winner(self):
        # Invert the weights via SSOT -> the shim now wins. If the weights were
        # baked in code this override would be ignored and APP would still win.
        cfg = """
            [mios-find.category_priority]
            mios-shim = 0
            windows-app = 9
        """
        winner, code, _ = run_ranker("foo", self.ENTRIES, cfg)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "SHIM")


class TierOrderingFromSSOT(unittest.TestCase):
    # "foobar" matches query "foo" at name_prefix; "a foo b" matches at
    # name_word. Default ordering ranks name_prefix above name_word.
    ENTRIES = [
        {"name": "foobar", "category": "windows-app", "launch": "PREFIX"},
        {"name": "a foo b", "category": "windows-app", "launch": "WORD"},
    ]

    def test_default_tier_order_prefix_beats_word(self):
        winner, code, _ = run_ranker("foo", self.ENTRIES, _NO_RANKER_CFG)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "PREFIX")

    def test_override_tier_order_flips_winner(self):
        # Reorder so name_word outranks name_prefix -> WORD wins.
        cfg = """
            [mios-find.ranker]
            tiers = ["name_exact", "name_word", "name_prefix", "name_substr",
                     "desc_word", "desc_substr", "fuzzy"]
        """
        winner, code, _ = run_ranker("foo", self.ENTRIES, cfg)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "WORD")


class FuzzyBoundsFromSSOT(unittest.TestCase):
    # Query "discrod" is a 2-edit typo of "discord" (token length 7).
    ENTRIES = [
        {"name": "discord", "category": "windows-app", "launch": "DISCORD"},
    ]

    def test_default_fuzzy_resolves_typo(self):
        winner, code, _ = run_ranker("discrod", self.ENTRIES, _NO_RANKER_CFG)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "DISCORD")

    def test_override_min_token_len_disables_fuzzy(self):
        # Require tokens >= 10 chars -> the 7-char query token is ineligible,
        # so the typo no longer matches -> no match (exit 1).
        cfg = """
            [mios-find.ranker]
            fuzzy_min_token_len = 10
            fuzzy_max_edit_distance = 2
        """
        winner, code, _ = run_ranker("discrod", self.ENTRIES, cfg)
        self.assertEqual(code, 1)
        self.assertIsNone(winner)

    def test_override_max_edit_distance_tightens_match(self):
        # Tighten to <=1 edit -> the 2-edit typo no longer matches.
        cfg = """
            [mios-find.ranker]
            fuzzy_min_token_len = 4
            fuzzy_max_edit_distance = 1
        """
        winner, code, _ = run_ranker("discrod", self.ENTRIES, cfg)
        self.assertEqual(code, 1)
        self.assertIsNone(winner)


class MultiTokenFuzzyMatching(unittest.TestCase):
    ENTRIES = [
        {"name": "mios-svc-forge", "category": "linux-flatpak", "launch": "FORGE"},
    ]

    def test_multi_token_query_requires_all_tokens_to_match(self):
        # "forza horizon" contains two tokens >=4 chars: "forza" and "horizon".
        # "forza" matches "forge" (edit dist 2), but "horizon" matches nothing.
        # It must NOT match because not all query tokens have a match.
        winner, code, _ = run_ranker("forza horizon", self.ENTRIES, _NO_RANKER_CFG)
        self.assertEqual(code, 1)
        self.assertIsNone(winner)

    def test_multi_token_typo_matches_when_all_tokens_match(self):
        # "wallpapr engine" contains "wallpapr" (matches "wallpaper" dist 1) and
        # "engine" (matches "engine" dist 0). Both match, so it must succeed.
        entries = [{"name": "wallpaper engine", "category": "windows-app", "launch": "WP"}]
        winner, code, _ = run_ranker("wallpapr engine", entries, _NO_RANKER_CFG)
        self.assertEqual(code, 0)
        self.assertEqual(winner, "WP")

if __name__ == "__main__":
    unittest.main(verbosity=2)

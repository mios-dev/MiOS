#!/usr/bin/env python3
# AI-hint: Executable proof of ADR-0016's central claim -- that offloading a service to another machine is purely an addressing change, achieved by an /etc/mios overlay with no file under usr/ edited. Each resolution runs in its OWN subprocess with MIOS_HOST_TOML set, because load_merged() caches per process and because that is how a booted host resolves. Also pins the measurement that corrects Decision 1: [urls] emits MIOS_URLS_* which no shipped code reads, while [ai].endpoint emits MIOS_AI_ENDPOINT which many do, so a service's canonical address is the key its consumers already resolve.
# AI-related: usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py, usr/share/doc/mios/adr/0016-blade-node-topology.md, tools/check-service-urls.py
"""Proof: a seat offloads its services by an /etc/mios overlay alone."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

BLADE = "blade-01.mesh.mios.local"

OVERLAY = """
[ai]
endpoint = "http://{b}:8700/v1"

[urls]
llm_light = "http://{b}:8500"
searxng   = "http://{b}:8800"
""".format(b=BLADE)

# Resolve in a child so the env is read at process start and no cache is shared.
_PROBE = (
    "import json,os,sys;"
    "sys.path.insert(0, os.path.join(%r,'usr','lib','mios'));"
    "import mios_toml;"
    "d = mios_toml.load_vendor() if os.environ.get('MIOS_PROBE_VENDOR') "
    "else mios_toml.load_merged();"
    "print(json.dumps({'ai': d.get('ai',{}).get('endpoint'),"
    " 'urls': d.get('urls',{})}))" % _ROOT
)


def _resolve(host_toml=None, vendor_only=False) -> dict:
    env = dict(os.environ)
    env.pop("MIOS_PROBE_VENDOR", None)
    if vendor_only:
        env["MIOS_PROBE_VENDOR"] = "1"
    if host_toml:
        env["MIOS_HOST_TOML"] = host_toml
    else:
        env["MIOS_HOST_TOML"] = os.devnull
    env["MIOS_USER_TOML"] = os.devnull
    out = subprocess.run([sys.executable, "-c", _PROBE], capture_output=True,
                         text=True, env=env, cwd=_ROOT)
    if out.returncode != 0:
        raise AssertionError("resolver failed: %s" % out.stderr.strip()[-400:])
    return json.loads(out.stdout)


def _usr_state() -> str:
    return subprocess.run(["git", "-C", _ROOT, "status", "--porcelain", "usr/"],
                          capture_output=True, text=True, check=False).stdout


class TestOffloadIsAnOverlay(unittest.TestCase):
    """ADR-0016 Decision 1: offload is an addressing change, nothing more."""

    def setUp(self):
        self.before = _usr_state()
        fd, self.overlay = tempfile.mkstemp(suffix=".toml")
        with os.fdopen(fd, "w") as fh:
            fh.write(OVERLAY)

    def tearDown(self):
        os.unlink(self.overlay)

    def test_vendor_tier_is_local(self):
        d = _resolve(vendor_only=True)
        self.assertIn("localhost", d["ai"])
        self.assertIn("localhost", d["urls"]["llm_light"])

    def test_overlay_repoints_the_ai_plane(self):
        self.assertIn(BLADE, _resolve(self.overlay)["ai"])

    def test_overlay_repoints_only_what_it_names(self):
        u = _resolve(self.overlay)["urls"]
        self.assertIn(BLADE, u["llm_light"])
        self.assertIn(BLADE, u["searxng"])
        self.assertIn("localhost", u["hermes"])   # not in the overlay -> stays local

    def test_without_the_overlay_everything_is_local(self):
        d = _resolve()
        self.assertIn("localhost", d["ai"])
        self.assertIn("localhost", d["urls"]["llm_light"])

    def test_no_file_under_usr_changed(self):
        _resolve(self.overlay)
        self.assertEqual(_usr_state(), self.before,
                         "offload must not require an edit under usr/")

    def test_empty_override_does_not_win(self):
        """Law 1: an empty string never overrides a non-empty value below it."""
        fd, path = tempfile.mkstemp(suffix=".toml")
        with os.fdopen(fd, "w") as fh:
            fh.write('[ai]\nendpoint = ""\n')
        try:
            self.assertIn("localhost", _resolve(path)["ai"])
        finally:
            os.unlink(path)


class TestCanonicalAddressIsTheKeyConsumersRead(unittest.TestCase):
    """The measurement that corrects Decision 1 -- pinned so it cannot rot back."""

    SKIP = ("usr/share/doc/", "usr/share/mios/reference/",
            "usr/share/mios/mios.toml", "usr/share/mios/names.generated.txt",
            "usr/share/mios/referenced_names.txt", "automation/lib/globals.",
            "automation/manifest.json", "tools/manifest.json", "docs/",
            "TASKS.md", "ROADMAP.md", "AGY-TASKS.md", "ADR.md", "tests/")

    def _consumers(self, var: str) -> int:
        out = subprocess.run(["git", "-C", _ROOT, "grep", "-l", var],
                             capture_output=True, text=True, check=False).stdout
        return len([f for f in out.split("\n") if f and not f.startswith(self.SKIP)])

    def test_ai_endpoint_is_read_by_real_consumers(self):
        self.assertGreater(self._consumers("MIOS_AI_ENDPOINT"), 5)

    def test_urls_table_is_still_read_by_nobody(self):
        # If this fails, [urls] gained a consumer: revisit ADR-0016 Decision 1
        # rather than deleting the assertion.
        for key in ("MIOS_URLS_LLM_LIGHT", "MIOS_URLS_SEARXNG",
                    "MIOS_URLS_PGVECTOR", "MIOS_URLS_HERMES"):
            self.assertEqual(self._consumers(key), 0, key)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# AI-hint: Two-sided verification test suite for unit hardening directives under ProtectSystem=strict (T-1139).
# AI-related: usr/lib/systemd/system/mios-agents.service, usr/lib/systemd/system/mios-cron-director.service, usr/lib/tmpfiles.d/, usr/libexec/mios/mios-agents-firstboot.sh
"""Two-sided verification controls for Task T-1139.

A ProtectSystem=strict unit must be able to write its state, and granting
that write must not take the state away from its owner:

* every StateDirectory= names a directory whose tmpfiles.d owner IS the
  unit's User=/Group= (root when unset) -- systemd recursively chowns an
  existing StateDirectory= to the unit's user, so a mismatch silently hands
  the directory to the wrong account on every start;
* the two units this task covers declare write access to their state;
* mios-agents-firstboot.sh, which runs as root, seeds the coder home with
  files owned by that home's owner, never root.

Each negative control plants the defect in a scratch copy and requires the
check to name it; the real tree is hashed before and after.
"""
from __future__ import annotations

import glob
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
_UNITS = os.path.join("usr", "lib", "systemd", "system")
_TMPFILES = os.path.join("usr", "lib", "tmpfiles.d")
_FIRSTBOOT = os.path.join("usr", "libexec", "mios", "mios-agents-firstboot.sh")


def parse_service_section(file_path: str) -> dict[str, list[str]]:
    """Directives of the [Service] section; a repeated key keeps every value."""
    directives: dict[str, list[str]] = {}
    in_service = False
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                in_service = line == "[Service]"
                continue
            if in_service and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                directives.setdefault(key.strip(), []).append(val.strip())
    return directives


def tmpfiles_owners(root_dir: str) -> dict[str, tuple[str, str]]:
    """path -> (user, group) for every d/D/v/q/Q line under usr/lib/tmpfiles.d."""
    owners: dict[str, tuple[str, str]] = {}
    for conf in sorted(glob.glob(os.path.join(root_dir, _TMPFILES, "*.conf"))):
        with open(conf, "r", encoding="utf-8") as f:
            for line in f:
                fields = line.split()
                if len(fields) >= 5 and fields[0] in ("d", "D", "v", "q", "Q"):
                    owners[fields[1].rstrip("/")] = (fields[3], fields[4])
    return owners


def _same_account(a: str, b: str) -> bool:
    return a == b or {a, b} == {"0", "root"}


def verify_state_directory_owners(root_dir: str) -> list[str]:
    """Every StateDirectory= must match its tmpfiles.d owner (no systemd chown)."""
    errors: list[str] = []
    owners = tmpfiles_owners(root_dir)
    for unit in sorted(glob.glob(os.path.join(root_dir, _UNITS, "*.service"))):
        svc = parse_service_section(unit)
        if svc.get("DynamicUser", ["no"])[-1] in ("yes", "true", "1"):
            continue
        user = svc.get("User", ["root"])[-1]
        group = svc.get("Group", [user])[-1]
        for entry in svc.get("StateDirectory", []):
            for rel in entry.split():
                path = "/var/lib/" + rel.split(":", 1)[0]
                if path not in owners:
                    continue
                t_user, t_group = owners[path]
                if not (_same_account(user, t_user) and _same_account(group, t_group)):
                    errors.append(
                        f"{os.path.basename(unit)}: StateDirectory={rel} runs as {user}:{group} "
                        f"but tmpfiles.d owns {path} as {t_user}:{t_group}; systemd would chown it"
                    )
    return errors


def verify_unit_directives(root_dir: str) -> list[str]:
    """The T-1139 units keep ProtectSystem=strict and can write their state."""
    errors: list[str] = []
    ag = parse_service_section(os.path.join(root_dir, _UNITS, "mios-agents.service"))
    if ag.get("ProtectSystem") != ["strict"]:
        errors.append("mios-agents.service missing ProtectSystem=strict")
    rw_agents = " ".join(ag.get("ReadWritePaths", [])).split()
    for need in ("/var/lib/mios/agents", "/var/lib/containers", "/run"):
        if need not in rw_agents:
            errors.append(f"mios-agents.service ReadWritePaths missing {need}")

    cr = parse_service_section(os.path.join(root_dir, _UNITS, "mios-cron-director.service"))
    if cr.get("ProtectSystem") != ["strict"]:
        errors.append("mios-cron-director.service missing ProtectSystem=strict")
    rw_cron = " ".join(cr.get("ReadWritePaths", [])).split()
    state_cron = " ".join(cr.get("StateDirectory", [])).split()
    if "/var/lib/mios/cron-director" not in rw_cron and "mios/cron-director" not in state_cron:
        errors.append("mios-cron-director.service cannot write /var/lib/mios/cron-director")
    return errors


def run_firstboot_seeders(script: str, home: str, ctx: str, ext: str) -> None:
    """Source the firstboot script and run only its seeders against a scratch home."""
    driver = (
        'set -euo pipefail; source "$1"; '
        'AGENTS_HOME="$2"; SETTINGS_SOURCE="$3/code-server-mobile-settings.json"; EXT_SOURCE="$4"; '
        "logger() { :; }; seed_code_server_settings; seed_code_server_extensions"
    )
    subprocess.run(["bash", "-c", driver, "seed", script, home, ctx, ext],
                   check=True, capture_output=True, text=True)


def verify_seeded_ownership(home: str) -> list[str]:
    """Every path seeded under home must carry home's owner."""
    want = os.stat(home)
    errors: list[str] = []
    seeded = 0
    for dirpath, dirnames, filenames in os.walk(home):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            st = os.lstat(path)
            seeded += 1
            if (st.st_uid, st.st_gid) != (want.st_uid, want.st_gid):
                errors.append(f"{os.path.relpath(path, home)} owned by {st.st_uid}:{st.st_gid}, "
                              f"home owner is {want.st_uid}:{want.st_gid}")
    if seeded == 0:
        errors.append("firstboot seeded nothing into the home (fixture is vacuous)")
    return errors


class TestT1139TwoSided(unittest.TestCase):
    def setUp(self) -> None:
        self.root = os.path.abspath(os.environ.get("MIOS_ROOT", _REPO_ROOT))
        self.watched = sorted(glob.glob(os.path.join(self.root, _UNITS, "*.service")))
        self.watched += sorted(glob.glob(os.path.join(self.root, _TMPFILES, "*.conf")))
        self.watched.append(os.path.join(self.root, _FIRSTBOOT))
        self.before = self._digest()

    def _digest(self) -> str:
        h = hashlib.sha256()
        for path in self.watched:
            with open(path, "rb") as f:
                h.update(path.encode() + b"\0" + f.read())
        return h.hexdigest()

    def _scratch_tree(self, scratch: str) -> None:
        for rel in (_UNITS, _TMPFILES):
            shutil.copytree(os.path.join(self.root, rel), os.path.join(scratch, rel))

    def _seed_fixture(self, scratch: str, script: str) -> str:
        home = os.path.join(scratch, "home")
        ctx = os.path.join(scratch, "ctx")
        ext = os.path.join(scratch, "ext")
        os.makedirs(home)
        os.makedirs(ctx)
        os.makedirs(ext)
        with open(os.path.join(ctx, "code-server-mobile-settings.json"), "w", encoding="utf-8") as f:
            f.write('{"window.zoomLevel": 0}\n')
        with open(os.path.join(ext, "package.json"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        os.chown(home, 1000, 1000)
        run_firstboot_seeders(script, home, ctx, ext)
        return home

    def test_positive_control(self) -> None:
        """The shipped tree: no chowning StateDirectory=, write paths declared."""
        self.assertEqual(verify_state_directory_owners(self.root), [])
        self.assertEqual(verify_unit_directives(self.root), [])

    def test_negative_control_state_directory_chown(self) -> None:
        """Re-plant StateDirectory=mios/agents on the root-run unit: it must be named."""
        with tempfile.TemporaryDirectory(prefix="t1139_neg_") as scratch:
            self._scratch_tree(scratch)
            unit = os.path.join(scratch, _UNITS, "mios-agents.service")
            with open(unit, "r", encoding="utf-8") as f:
                text = f.read()
            planted = re.sub(r"^ReadWritePaths=", "StateDirectory=mios/agents\nReadWritePaths=",
                             text, count=1, flags=re.MULTILINE)
            self.assertNotEqual(planted, text, "plant did not apply")
            with open(unit, "w", encoding="utf-8") as f:
                f.write(planted)
            errs = verify_state_directory_owners(scratch)
            self.assertEqual(len(errs), 1, errs)
            self.assertIn("mios-agents.service: StateDirectory=mios/agents runs as root:root", errs[0])

    def test_negative_control_write_paths(self) -> None:
        """Drop each unit's write grant: the check must name the unit."""
        with tempfile.TemporaryDirectory(prefix="t1139_neg_") as scratch:
            self._scratch_tree(scratch)
            for name, expect in (("mios-agents.service", "mios-agents.service ReadWritePaths missing /var/lib/mios/agents"),
                                 ("mios-cron-director.service", "mios-cron-director.service cannot write")):
                unit = os.path.join(scratch, _UNITS, name)
                with open(unit, "r", encoding="utf-8") as f:
                    text = f.read()
                with open(unit, "w", encoding="utf-8") as f:
                    f.write(re.sub(r"^(ReadWritePaths|StateDirectory)=.*$", "", text, flags=re.MULTILINE))
                errs = verify_unit_directives(scratch)
                self.assertTrue(any(e.startswith(expect) for e in errs), errs)
                with open(unit, "w", encoding="utf-8") as f:
                    f.write(text)

    @unittest.skipUnless(os.geteuid() == 0, "ownership fixture needs root to chown the scratch home")
    def test_firstboot_seeds_as_home_owner(self) -> None:
        """Positive: seeding a uid-1000 home as root leaves every seeded path uid 1000."""
        with tempfile.TemporaryDirectory(prefix="t1139_seed_") as scratch:
            home = self._seed_fixture(scratch, os.path.join(self.root, _FIRSTBOOT))
            self.assertEqual(verify_seeded_ownership(home), [])
            self.assertTrue(os.path.isfile(os.path.join(
                home, ".local/share/code-server/User/settings.json")))

    @unittest.skipUnless(os.geteuid() == 0, "ownership fixture needs root to chown the scratch home")
    def test_negative_control_firstboot_root_owned(self) -> None:
        """Plant the pre-fix seeding (plain install -d / install / cp as root): named."""
        with tempfile.TemporaryDirectory(prefix="t1139_neg_") as scratch:
            with open(os.path.join(self.root, _FIRSTBOOT), "r", encoding="utf-8") as f:
                text = f.read()
            planted = text.replace(' -o "${owner%:*}" -g "${owner#*:}"', "")
            planted = planted.replace('        chown -R "$(home_owner)" "$ext_target"\n', "")
            self.assertNotEqual(planted, text, "plant did not apply")
            script = os.path.join(scratch, "firstboot.sh")
            with open(script, "w", encoding="utf-8") as f:
                f.write(planted)
            errs = verify_seeded_ownership(self._seed_fixture(scratch, script))
            self.assertTrue(errs, "root-owned seeding went undetected")
            self.assertIn(".local owned by 0:0", "\n".join(errs))

    def tearDown(self) -> None:
        self.assertEqual(self._digest(), self.before, "real tree mutated during test")


if __name__ == "__main__":
    unittest.main()

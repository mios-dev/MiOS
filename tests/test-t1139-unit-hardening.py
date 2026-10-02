#!/usr/bin/env python3
# AI-hint: Two-sided verification test suite for unit hardening directives under ProtectSystem=strict (T-1139).
# AI-related: usr/lib/systemd/system/mios-agents.service, usr/lib/systemd/system/mios-cron-director.service, usr/share/mios/mios.toml
"""Two-sided verification controls for Task T-1139.

Positive control: Validates presence of ProtectSystem=strict, StateDirectory,
and ReadWritePaths directives across mios-agents.service and mios-cron-director.service.
Negative control: Plants defects in an isolated temporary scratch copy,
verifies detection with named defect diagnostics, and confirms the real tree remains pristine.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


def parse_service_section(file_path: str) -> dict[str, str]:
    """Parse directives from the [Service] section of a systemd unit file."""
    directives: dict[str, str] = {}
    in_service = False
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                in_service = (line == "[Service]")
                continue
            if in_service and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                directives[key.strip()] = val.strip()
    return directives


def verify_unit_directives(root_dir: str) -> list[str]:
    """Validate hardening and write path compliance for T-1139 units."""
    errors: list[str] = []
    agents_path = os.path.join(root_dir, "usr", "lib", "systemd", "system", "mios-agents.service")
    cron_path = os.path.join(root_dir, "usr", "lib", "systemd", "system", "mios-cron-director.service")

    # 1. mios-agents.service
    if not os.path.isfile(agents_path):
        return [f"Missing unit file: {agents_path}"]
    ag = parse_service_section(agents_path)
    if ag.get("ProtectSystem") != "strict":
        errors.append("mios-agents.service missing ProtectSystem=strict")
    if ag.get("StateDirectory") != "mios/agents":
        errors.append("mios-agents.service missing StateDirectory=mios/agents")
    rw_agents = ag.get("ReadWritePaths", "").split()
    if not ("/var/lib/containers" in rw_agents and "/run" in rw_agents):
        errors.append("mios-agents.service missing ReadWritePaths containing /var/lib/containers and /run")

    # 2. mios-cron-director.service
    if not os.path.isfile(cron_path):
        return [f"Missing unit file: {cron_path}"]
    cr = parse_service_section(cron_path)
    if cr.get("ProtectSystem") != "strict":
        errors.append("mios-cron-director.service missing ProtectSystem=strict")
    if cr.get("StateDirectory") != "mios/cron-director":
        errors.append("mios-cron-director.service missing StateDirectory=mios/cron-director")
    if cr.get("StateDirectoryMode") != "0770":
        errors.append("mios-cron-director.service missing StateDirectoryMode=0770")
    rw_cron = cr.get("ReadWritePaths", "").split()
    if "/var/lib/mios/cron-director" not in rw_cron:
        errors.append("mios-cron-director.service missing ReadWritePaths=/var/lib/mios/cron-director")

    return errors


class TestT1139TwoSided(unittest.TestCase):
    def setUp(self) -> None:
        self.root = os.path.abspath(os.environ.get("MIOS_ROOT", _REPO_ROOT))
        self.agents_rel = os.path.join("usr", "lib", "systemd", "system", "mios-agents.service")
        self.cron_rel = os.path.join("usr", "lib", "systemd", "system", "mios-cron-director.service")
        self.agents_real = os.path.join(self.root, self.agents_rel)
        self.cron_real = os.path.join(self.root, self.cron_rel)

        # Record real-tree sha256 hashes
        with open(self.agents_real, "rb") as f:
            self.hash_agents = hashlib.sha256(f.read()).hexdigest()
        with open(self.cron_real, "rb") as f:
            self.hash_cron = hashlib.sha256(f.read()).hexdigest()

    def test_positive_control(self) -> None:
        """Positive Control: Verify real tree units satisfy all T-1139 directives."""
        errors = verify_unit_directives(self.root)
        self.assertEqual(errors, [], f"T-1139 positive control failed: {errors}")

    def test_negative_control_scratch_isolation(self) -> None:
        """Negative Control: Plant defects in isolated scratch tree and assert detection."""
        with tempfile.TemporaryDirectory(prefix="t1139_neg_") as scratch:
            scratch_units = os.path.join(scratch, "usr", "lib", "systemd", "system")
            os.makedirs(scratch_units, exist_ok=True)
            scratch_agents = os.path.join(scratch, self.agents_rel)
            scratch_cron = os.path.join(scratch, self.cron_rel)
            shutil.copy2(self.agents_real, scratch_agents)
            shutil.copy2(self.cron_real, scratch_cron)

            # Defect 1: Omit StateDirectory from scratch mios-agents.service
            with open(scratch_agents, "r", encoding="utf-8") as f:
                content = f.read()
            bad_content = re.sub(r"^StateDirectory=.*$", "", content, flags=re.MULTILINE)
            with open(scratch_agents, "w", encoding="utf-8") as f:
                f.write(bad_content)
            errs = verify_unit_directives(scratch)
            self.assertIn("mios-agents.service missing StateDirectory=mios/agents", errs)

            # Restore and Defect 2: Omit ReadWritePaths from scratch mios-agents.service
            with open(scratch_agents, "w", encoding="utf-8") as f:
                f.write(content)
            bad_content = re.sub(r"^ReadWritePaths=.*$", "", content, flags=re.MULTILINE)
            with open(scratch_agents, "w", encoding="utf-8") as f:
                f.write(bad_content)
            errs = verify_unit_directives(scratch)
            self.assertIn("mios-agents.service missing ReadWritePaths containing /var/lib/containers and /run", errs)

            # Defect 3: Omit StateDirectory from scratch mios-cron-director.service
            with open(scratch_cron, "r", encoding="utf-8") as f:
                c_content = f.read()
            bad_c = re.sub(r"^StateDirectory=.*$", "", c_content, flags=re.MULTILINE)
            with open(scratch_cron, "w", encoding="utf-8") as f:
                f.write(bad_c)
            errs = verify_unit_directives(scratch)
            self.assertIn("mios-cron-director.service missing StateDirectory=mios/cron-director", errs)

            # Defect 4: Omit ReadWritePaths from scratch mios-cron-director.service
            with open(scratch_cron, "w", encoding="utf-8") as f:
                f.write(c_content)
            bad_c = re.sub(r"^ReadWritePaths=.*$", "", c_content, flags=re.MULTILINE)
            with open(scratch_cron, "w", encoding="utf-8") as f:
                f.write(bad_c)
            errs = verify_unit_directives(scratch)
            self.assertIn("mios-cron-director.service missing ReadWritePaths=/var/lib/mios/cron-director", errs)

    def tearDown(self) -> None:
        # Invariant check: real tree sha256 sums must remain identical
        with open(self.agents_real, "rb") as f:
            now_agents = hashlib.sha256(f.read()).hexdigest()
        with open(self.cron_real, "rb") as f:
            now_cron = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(now_agents, self.hash_agents, "Real mios-agents.service mutated during test!")
        self.assertEqual(now_cron, self.hash_cron, "Real mios-cron-director.service mutated during test!")


if __name__ == "__main__":
    unittest.main()

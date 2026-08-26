#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Ceph RADOS Gateway Quadlet container configuration.
# AI-related: usr/share/containers/systemd/mios-radosgw.container, usr/share/mios/mios.toml
"""Automated tests for Ceph RADOS Gateway Quadlet container unit syntax, port binding, and health checks."""

from __future__ import annotations

import configparser
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


class TestRADOSGWGateway(unittest.TestCase):
    """Validates Quadlet container unit definition, port binding, S3 configuration, and localhost isolation."""

    def setUp(self):
        self.quadlet_path = os.path.join(
            _ROOT, "usr", "share", "containers", "systemd", "mios-radosgw.container"
        )

    def test_quadlet_file_exists(self):
        self.assertTrue(
            os.path.exists(self.quadlet_path),
            f"Quadlet file missing at {self.quadlet_path}",
        )

    def test_quadlet_sections_and_syntax(self):
        with open(self.quadlet_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check raw lines
        self.assertIn("[Unit]", content)
        self.assertIn("[Container]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)

    def test_localhost_port_binding_and_no_wan_exposure(self):
        """Verify the S3 gateway port is strictly bound to 127.0.0.1 or mesh, not 0.0.0.0."""
        with open(self.quadlet_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        publish_lines = [l for l in lines if l.startswith("PublishPort=")]
        self.assertTrue(len(publish_lines) > 0, "Missing PublishPort in mios-radosgw.container")

        for pl in publish_lines:
            val = pl.split("=", 1)[1].strip()
            # Must be bound to 127.0.0.1
            self.assertTrue(
                val.startswith("127.0.0.1:"),
                f"PublishPort '{val}' must explicitly bind to 127.0.0.1 to prevent WAN exposure",
            )
            self.assertIn("8470", val, f"Port 8470 must be referenced in '{val}'")

    def test_container_name_and_image(self):
        with open(self.quadlet_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("ContainerName=mios-radosgw", content)
        self.assertIn("Image=quay.io/ceph/ceph", content)
        self.assertIn("Restart=always", content)

    def test_volume_mounts(self):
        with open(self.quadlet_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        vol_lines = [l.split("=", 1)[1].strip() for l in lines if l.startswith("Volume=")]
        self.assertTrue(any("/etc/ceph" in v for v in vol_lines), "Missing /etc/ceph volume mount")
        self.assertTrue(any("/var/lib/ceph" in v for v in vol_lines), "Missing /var/lib/ceph volume mount")
        self.assertTrue(any("radosgw" in v for v in vol_lines), "Missing radosgw data volume mount")

    def test_healthcheck_configuration(self):
        with open(self.quadlet_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("HealthCmd=", content)
        self.assertIn("curl", content)
        self.assertIn("8470", content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRADOSGWGateway)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

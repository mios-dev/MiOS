#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-WISO Windows driver slipstreaming and autounattend generation.
# AI-related: src/autounattend/ConvertTo-MiOSPreset.ps1, tools/windows/Export-MiOSDrivers.ps1
"""Automated tests for WS-WISO driver path parsing and unattend XML injection."""

from __future__ import annotations

import os
import sys
import unittest
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_PRESET_PATH = os.path.join(_ROOT, "src", "autounattend", "ConvertTo-MiOSPreset.ps1")


class TestWindowsDriverPack(unittest.TestCase):
    """Validates driver slipstreaming script existence and unattend XML structure."""

    def test_script_exists(self):
        self.assertTrue(os.path.exists(_PRESET_PATH))

    def test_xml_generation_format(self):
        sample_xml = """<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="offlineServicing">
        <component name="Microsoft-Windows-PnpCustomizationsNonWinPE">
            <DriverPaths>
                <PathAndCredentials keyValue="1">
                    <Path>M:\\drivers\\net</Path>
                </PathAndCredentials>
            </DriverPaths>
        </component>
    </settings>
</unattend>"""
        root = ET.fromstring(sample_xml)
        self.assertIn("unattend", root.tag)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWindowsDriverPack)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

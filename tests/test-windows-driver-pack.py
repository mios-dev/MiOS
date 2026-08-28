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
        """The preset script is present when the tree carries it.

        `src/autounattend/*` is git-ignored (.gitignore un-ignores the directory
        and then excludes its contents), so this script exists in a developer's
        working tree but never in a clean checkout -- which is why this assertion
        passed locally and failed on every runner. Tracking it is not the fix
        either: it is 56 lines of PowerShell against a shrink-only ps_lines
        ceiling that Law 14 keeps there deliberately. Skip where it cannot
        exist, and say so, rather than assert a file the repo excludes.
        """
        if not os.path.exists(_PRESET_PATH):
            raise unittest.SkipTest(
                f"{_PRESET_PATH} is not in this tree: src/autounattend/* is git-ignored")
        self.assertTrue(os.path.isfile(_PRESET_PATH))

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

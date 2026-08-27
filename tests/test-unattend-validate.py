#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Windows autounattend.xml schema validator.
# AI-related: usr/libexec/mios/win/unattend_validate.py, autounattend.xml
"""Unit and integration test suite for UnattendValidator and unattend_validate CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "win", "unattend_validate.py")

spec = importlib.util.spec_from_file_location("unattend_validate", _TARGET_PATH)
if spec and spec.loader:
    unattend_validate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = unattend_validate
    spec.loader.exec_module(unattend_validate)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


VALID_XML_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend"
          xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <settings pass="windowsPE">
    <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <Display>
        <HorizontalResolution>1920</HorizontalResolution>
        <VerticalResolution>1080</VerticalResolution>
        <ColorDepth>32</ColorDepth>
      </Display>
      <UserData>
        <ProductKey>
          <Key>VK7JG-NPHTM-C97JM-9MPGT-3V66T</Key>
          <WillShowUI>OnError</WillShowUI>
        </ProductKey>
        <AcceptEula>true</AcceptEula>
      </UserData>
      <DiskConfiguration>
        <Disk>
          <DiskID>0</DiskID>
          <WillWipeDisk>true</WillWipeDisk>
          <CreatePartitions>
            <CreatePartition><Order>1</Order><Type>EFI</Type></CreatePartition>
            <CreatePartition><Order>2</Order><Type>Primary</Type></CreatePartition>
          </CreatePartitions>
        </Disk>
      </DiskConfiguration>
      <RunSynchronous>
        <RunSynchronousCommand wcm:action="add"><Order>1</Order><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassTPMCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add"><Order>2</Order><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassSecureBootCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add"><Order>3</Order><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassRAMCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add"><Order>4</Order><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassStorageCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add"><Order>5</Order><Path>reg add HKLM\\SYSTEM\\Setup\\LabConfig /v BypassCPUCheck /t REG_DWORD /d 1 /f</Path></RunSynchronousCommand>
      </RunSynchronous>
    </component>
  </settings>
  <settings pass="specialize">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <ComputerName>MIOS-DEV</ComputerName>
      <TimeZone>UTC</TimeZone>
    </component>
  </settings>
  <settings pass="oobeSystem">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <AutoLogon>
        <Enabled>true</Enabled>
        <LogonCount>1</LogonCount>
        <Username>mios</Username>
      </AutoLogon>
      <OOBE>
        <HideEULAPage>true</HideEULAPage>
        <HideLocalAccountScreen>true</HideLocalAccountScreen>
        <ProtectYourPC>3</ProtectYourPC>
      </OOBE>
    </component>
  </settings>
</unattend>
"""


class TestUnattendValidate(unittest.TestCase):
    """Test suite for Windows autounattend XML schema validation."""

    def setUp(self):
        self.validator = unattend_validate.UnattendValidator(strict=False)

    def test_valid_xml_string_passes(self):
        res = self.validator.validate_xml_string(VALID_XML_SAMPLE)
        self.assertTrue(res.valid)
        self.assertEqual(res.error_count, 0)
        self.assertEqual(res.warning_count, 0)
        self.assertIn("windowsPE", res.passes_found)
        self.assertIn("specialize", res.passes_found)
        self.assertIn("oobeSystem", res.passes_found)
        # All 5 Win11 bypasses must be detected
        self.assertTrue(all(res.hardware_bypasses.values()))

    def test_validate_repo_autounattend_xml(self):
        repo_xml = os.path.join(_ROOT, "autounattend.xml")
        if os.path.exists(repo_xml):
            res = self.validator.validate_file(repo_xml)
            self.assertTrue(res.valid, f"autounattend.xml failed validation: {res.errors}")
            self.assertEqual(res.error_count, 0)

    def test_missing_default_namespace_raises_error(self):
        xml = '<unattend><settings pass="windowsPE"></settings></unattend>'
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-003", rule_ids)

    def test_malformed_xml_syntax_raises_error(self):
        xml = '<unattend xmlns="urn:schemas-microsoft-com:unattend"><unclosed>'
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        self.assertEqual(res.errors[0].rule_id, "UNATTEND-001")

    def test_missing_settings_pass_attribute(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings>
            <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" />
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-010", rule_ids)

    def test_invalid_processor_architecture(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="windowsPE">
            <component name="Microsoft-Windows-Setup" processorArchitecture="invalid_mips" publicKeyToken="31bf3856ad364e35" />
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-022", rule_ids)

    def test_invalid_display_resolution_and_colordepth(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="windowsPE">
            <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35">
              <Display>
                <HorizontalResolution>320</HorizontalResolution>
                <VerticalResolution>240</VerticalResolution>
                <ColorDepth>8</ColorDepth>
              </Display>
            </component>
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-030", rule_ids)

    def test_invalid_product_key_format(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="windowsPE">
            <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35">
              <UserData>
                <ProductKey><Key>NOT-A-VALID-KEY</Key></ProductKey>
              </UserData>
            </component>
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-032", rule_ids)

    def test_duplicate_run_synchronous_order(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="windowsPE">
            <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35">
              <RunSynchronous>
                <RunSynchronousCommand><Order>1</Order><Path>cmd1</Path></RunSynchronousCommand>
                <RunSynchronousCommand><Order>1</Order><Path>cmd2</Path></RunSynchronousCommand>
              </RunSynchronous>
            </component>
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-036", rule_ids)

    def test_invalid_computer_name_length_and_characters(self):
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="specialize">
            <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35">
              <ComputerName>TOO_LONG_COMPUTER_NAME_OVER_15_CHARS</ComputerName>
            </component>
          </settings>
        </unattend>"""
        res = self.validator.validate_xml_string(xml)
        self.assertFalse(res.valid)
        rule_ids = [e.rule_id for e in res.errors]
        self.assertIn("UNATTEND-039", rule_ids)

    def test_strict_mode_fails_on_warnings(self):
        strict_val = unattend_validate.UnattendValidator(strict=True)
        # XML without xmlns:wcm (generates warning)
        xml = """<unattend xmlns="urn:schemas-microsoft-com:unattend">
          <settings pass="windowsPE">
            <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" />
          </settings>
        </unattend>"""
        res = strict_val.validate_xml_string(xml)
        self.assertFalse(res.valid)
        self.assertGreaterEqual(res.warning_count, 1)

    def test_missing_file_returns_error(self):
        res = self.validator.validate_file("/nonexistent/autounattend.xml")
        self.assertFalse(res.valid)
        self.assertEqual(res.errors[0].rule_id, "UNATTEND-000")

    def test_cli_mock_execution(self):
        test_args = ["unattend_validate.py", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = unattend_validate.main()
            self.assertEqual(exit_code, 0)

    def test_cli_xml_string_argument(self):
        test_args = ["unattend_validate.py", "--xml", VALID_XML_SAMPLE, "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = unattend_validate.main()
            self.assertEqual(exit_code, 0)

    def test_cli_file_argument(self):
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as tf:
            tf.write(VALID_XML_SAMPLE)
            tf_path = tf.name

        try:
            test_args = ["unattend_validate.py", "--file", tf_path, "--json"]
            with patch.object(sys, "argv", test_args):
                exit_code = unattend_validate.main()
                self.assertEqual(exit_code, 0)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnattendValidate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

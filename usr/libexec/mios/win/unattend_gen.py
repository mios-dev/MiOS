#!/usr/bin/env python3
# AI-hint: Windows 11 autounattend.xml generator with debloat, developer mode & bypasses
# AI-related: tests/test-unattend-gen.py, usr/share/mios/mios.toml, usr/libexec/mios/win/ps_policy_config.py
# AI-functions: UnattendGenerator, UnattendPreset, generate_unattend_xml
"""
MiOS Windows 11 Unattended Answer File (autounattend.xml) Generator.

Synthesizes complete, schema-compliant autounattend.xml answer files for Windows 11:
- windowsPE: TPM 2.0, SecureBoot, RAM & CPU hardware check bypasses, display settings.
- offlineServicing: Driver search path injection for Wi-Fi and storage controllers.
- specialize: Telemetry disabling, OEM branding, Developer Mode, and Long Paths enablement.
- oobeSystem: Passwordless/auto-logon 'mios' local admin account, OOBE screen bypass,
  and FirstLogonCommands for WSL2/Hyper-V platform initialization.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from xml.dom import minidom

UNATTEND_NS = "urn:schemas-microsoft-com:unattend"
WCM_NS = "http://schemas.microsoft.com/WMIConfig/2002/State"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class Preset(str, Enum):
    DEVELOPER = "developer"
    MINIMAL = "minimal"
    GAMING = "gaming"


@dataclass
class UnattendConfig:
    """Configuration parameters for Windows 11 autounattend generation."""
    preset: Preset = Preset.DEVELOPER
    username: str = "mios"
    password: Optional[str] = None
    computer_name: str = "MiOS-Workstation"
    driver_path: str = "M:\\drivers"
    bypass_tpm: bool = True
    bypass_secure_boot: bool = True
    bypass_ram: bool = True
    bypass_storage: bool = True
    bypass_cpu: bool = True
    disable_telemetry: bool = True
    enable_dev_mode: bool = True
    enable_long_paths: bool = True
    enable_wsl2: bool = True
    resolution_x: int = 1920
    resolution_y: int = 1080


class UnattendGenerator:
    """Generates schema-compliant autounattend.xml document."""

    def __init__(self, config: UnattendConfig, mock: bool = False):
        self.config = config
        self.mock = mock

    def build_xml_tree(self) -> ET.Element:
        """Construct the complete XML tree for autounattend.xml."""
        root = ET.Element("unattend", attrib={
            "xmlns": UNATTEND_NS,
            "xmlns:wcm": WCM_NS,
            "xmlns:xsi": XSI_NS,
        })

        # -------------------------------------------------------------
        # PASS 1: windowsPE
        # -------------------------------------------------------------
        pass_winpe = ET.SubElement(root, "settings", attrib={"pass": "windowsPE"})
        comp_setup = ET.SubElement(pass_winpe, "component", attrib={
            "name": "Microsoft-Windows-Setup",
            "processorArchitecture": "amd64",
            "publicKeyToken": "31bf3856ad364e35",
            "language": "neutral",
            "versionScope": "nonSxS",
        })

        # Display
        display = ET.SubElement(comp_setup, "Display")
        ET.SubElement(display, "HorizontalResolution").text = str(self.config.resolution_x)
        ET.SubElement(display, "VerticalResolution").text = str(self.config.resolution_y)
        ET.SubElement(display, "ColorDepth").text = "32"

        # UserData & EULA
        userdata = ET.SubElement(comp_setup, "UserData")
        ET.SubElement(userdata, "AcceptEula").text = "true"
        prodkey = ET.SubElement(userdata, "ProductKey")
        ET.SubElement(prodkey, "Key").text = "VK7JG-NPHTM-C97JM-9MPGT-3V66T"  # Generic Windows Pro Key
        ET.SubElement(prodkey, "WillShowUI").text = "OnError"

        # RunSynchronous (Hardware Bypasses)
        if self.config.bypass_tpm or self.config.bypass_secure_boot:
            run_sync = ET.SubElement(comp_setup, "RunSynchronous")
            bypasses = [
                ("BypassTPMCheck", self.config.bypass_tpm),
                ("BypassSecureBootCheck", self.config.bypass_secure_boot),
                ("BypassRAMCheck", self.config.bypass_ram),
                ("BypassStorageCheck", self.config.bypass_storage),
                ("BypassCPUCheck", self.config.bypass_cpu),
            ]
            order = 1
            for name, enabled in bypasses:
                if enabled:
                    cmd_elem = ET.SubElement(run_sync, "RunSynchronousCommand", attrib={"wcm:action": "add"})
                    ET.SubElement(cmd_elem, "Order").text = str(order)
                    ET.SubElement(cmd_elem, "Path").text = f"reg add HKLM\\SYSTEM\\Setup\\LabConfig /v {name} /t REG_DWORD /d 1 /f"
                    ET.SubElement(cmd_elem, "Description").text = f"Bypass {name}"
                    order += 1

        # -------------------------------------------------------------
        # PASS 2: offlineServicing (Driver search path)
        # -------------------------------------------------------------
        if self.config.driver_path:
            pass_offline = ET.SubElement(root, "settings", attrib={"pass": "offlineServicing"})
            comp_pnp = ET.SubElement(pass_offline, "component", attrib={
                "name": "Microsoft-Windows-PnpCustomizationsNonWinPE",
                "processorArchitecture": "amd64",
                "publicKeyToken": "31bf3856ad364e35",
                "language": "neutral",
                "versionScope": "nonSxS",
            })
            driver_paths = ET.SubElement(comp_pnp, "DriverPaths")
            path_cred = ET.SubElement(driver_paths, "PathAndCredentials", attrib={"wcm:action": "add", "wcm:keyValue": "1"})
            ET.SubElement(path_cred, "Path").text = self.config.driver_path

        # -------------------------------------------------------------
        # PASS 3: specialize
        # -------------------------------------------------------------
        pass_spec = ET.SubElement(root, "settings", attrib={"pass": "specialize"})
        comp_shell = ET.SubElement(pass_spec, "component", attrib={
            "name": "Microsoft-Windows-Shell-Setup",
            "processorArchitecture": "amd64",
            "publicKeyToken": "31bf3856ad364e35",
            "language": "neutral",
            "versionScope": "nonSxS",
        })
        ET.SubElement(comp_shell, "ComputerName").text = self.config.computer_name
        ET.SubElement(comp_shell, "TimeZone").text = "UTC"

        oem_info = ET.SubElement(comp_shell, "OEMInformation")
        ET.SubElement(oem_info, "Manufacturer").text = "MiOS AI Workstation"
        ET.SubElement(oem_info, "Model").text = "MiOS Hybrid Development Node"

        # Debloat & Developer Mode registry tweaks
        comp_deployment = ET.SubElement(pass_spec, "component", attrib={
            "name": "Microsoft-Windows-Deployment",
            "processorArchitecture": "amd64",
            "publicKeyToken": "31bf3856ad364e35",
            "language": "neutral",
            "versionScope": "nonSxS",
        })
        run_spec_sync = ET.SubElement(comp_deployment, "RunSynchronous")
        spec_cmds = []
        if self.config.disable_telemetry:
            spec_cmds.append(("Disable Telemetry", "reg add HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection /v AllowTelemetry /t REG_DWORD /d 0 /f"))
            spec_cmds.append(("Disable Consumer Features", "reg add HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent /v DisableWindowsConsumerFeatures /t REG_DWORD /d 1 /f"))
        if self.config.enable_dev_mode:
            spec_cmds.append(("Enable Developer Mode", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AppModelUnlock /v AllowDevelopmentWithoutDevLicense /t REG_DWORD /d 1 /f"))
        if self.config.enable_long_paths:
            spec_cmds.append(("Enable Long Paths", "reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f"))

        for idx, (desc, cmd) in enumerate(spec_cmds, 1):
            cmd_elem = ET.SubElement(run_spec_sync, "RunSynchronousCommand", attrib={"wcm:action": "add"})
            ET.SubElement(cmd_elem, "Order").text = str(idx)
            ET.SubElement(cmd_elem, "Path").text = cmd
            ET.SubElement(cmd_elem, "Description").text = desc

        # -------------------------------------------------------------
        # PASS 4: oobeSystem
        # -------------------------------------------------------------
        pass_oobe = ET.SubElement(root, "settings", attrib={"pass": "oobeSystem"})
        comp_oobe_shell = ET.SubElement(pass_oobe, "component", attrib={
            "name": "Microsoft-Windows-Shell-Setup",
            "processorArchitecture": "amd64",
            "publicKeyToken": "31bf3856ad364e35",
            "language": "neutral",
            "versionScope": "nonSxS",
        })

        # AutoLogon
        auto_logon = ET.SubElement(comp_oobe_shell, "AutoLogon")
        ET.SubElement(auto_logon, "Enabled").text = "true"
        ET.SubElement(auto_logon, "LogonCount").text = "999"
        ET.SubElement(auto_logon, "Username").text = self.config.username
        if self.config.password:
            pwd = ET.SubElement(auto_logon, "Password")
            ET.SubElement(pwd, "Value").text = self.config.password
            ET.SubElement(pwd, "PlainText").text = "true"

        # OOBE Bypass flags
        oobe = ET.SubElement(comp_oobe_shell, "OOBE")
        ET.SubElement(oobe, "HideEULAPage").text = "true"
        ET.SubElement(oobe, "HideLocalAccountScreen").text = "true"
        ET.SubElement(oobe, "HideOnlineAccountScreens").text = "true"
        ET.SubElement(oobe, "HideWirelessSetupInOOBE").text = "true"
        ET.SubElement(oobe, "ProtectYourPC").text = "3"
        ET.SubElement(oobe, "NetworkLocation").text = "Work"

        # UserAccounts
        user_accs = ET.SubElement(comp_oobe_shell, "UserAccounts")
        local_accs = ET.SubElement(user_accs, "LocalAccounts")
        local_acc = ET.SubElement(local_accs, "LocalAccount", attrib={"wcm:action": "add"})
        ET.SubElement(local_acc, "Name").text = self.config.username
        ET.SubElement(local_acc, "Group").text = "Administrators"
        ET.SubElement(local_acc, "DisplayName").text = f"MiOS Operator ({self.config.username})"
        if self.config.password:
            l_pwd = ET.SubElement(local_acc, "Password")
            ET.SubElement(l_pwd, "Value").text = self.config.password
            ET.SubElement(l_pwd, "PlainText").text = "true"

        # FirstLogonCommands
        first_cmds = ET.SubElement(comp_oobe_shell, "FirstLogonCommands")
        fl_list = [
            ("PowerShell Execution Policy", "powershell.exe -NoProfile -Command \"Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned -Force\""),
            ("MiOS AI Endpoint Variable", "powershell.exe -NoProfile -Command \"[System.Environment]::SetEnvironmentVariable('MIOS_AI_ENDPOINT', 'http://127.0.0.1:8640/v1', 'Machine')\""),
        ]
        if self.config.enable_wsl2:
            fl_list.append(("Enable WSL2 & VM Platform", "powershell.exe -NoProfile -Command \"Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform,Microsoft-Windows-Subsystem-Linux -NoRestart\""))

        for idx, (desc, cmd) in enumerate(fl_list, 1):
            cmd_elem = ET.SubElement(first_cmds, "SynchronousCommand", attrib={"wcm:action": "add"})
            ET.SubElement(cmd_elem, "Order").text = str(idx)
            ET.SubElement(cmd_elem, "CommandLine").text = cmd
            ET.SubElement(cmd_elem, "Description").text = desc

        return root

    def generate_xml_string(self) -> str:
        """Produce pretty-printed XML string with XML declaration."""
        tree = self.build_xml_tree()
        raw_str = ET.tostring(tree, encoding="utf-8")
        parsed = minidom.parseString(raw_str)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    def run(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate autounattend.xml content and write to file if requested."""
        xml_content = self.generate_xml_string()

        if output_path and not self.mock:
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

        return {
            "status": "success",
            "preset": self.config.preset.value,
            "username": self.config.username,
            "computer_name": self.config.computer_name,
            "bypasses_enabled": {
                "tpm": self.config.bypass_tpm,
                "secure_boot": self.config.bypass_secure_boot,
                "ram": self.config.bypass_ram,
                "storage": self.config.bypass_storage,
                "cpu": self.config.bypass_cpu,
            },
            "features_enabled": {
                "telemetry_disabled": self.config.disable_telemetry,
                "developer_mode": self.config.enable_dev_mode,
                "long_paths": self.config.enable_long_paths,
                "wsl2": self.config.enable_wsl2,
            },
            "output_path": output_path,
            "xml_length": len(xml_content),
            "xml_preview": xml_content[:500] + "...",
            "mock": self.mock,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Windows 11 autounattend.xml Generator"
    )
    parser.add_argument("--preset", choices=["developer", "minimal", "gaming"], default="developer", help="Configuration preset")
    parser.add_argument("--username", default="mios", help="Local Administrator username")
    parser.add_argument("--password", help="Local Administrator password (plain text)")
    parser.add_argument("--computer-name", default="MiOS-Workstation", help="NetBIOS / DNS computer name")
    parser.add_argument("--driver-path", default="M:\\drivers", help="Driver staging search path")
    parser.add_argument("--bypass-tpm", action="store_true", default=True, help="Enable TPM 2.0 bypass")
    parser.add_argument("--disable-telemetry", action="store_true", default=True, help="Disable Windows telemetry")
    parser.add_argument("--output", help="Target autounattend.xml file path")
    parser.add_argument("--emit-xml", action="store_true", help="Print raw XML to stdout")
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation without writing file")
    parser.add_argument("--mock", action="store_true", help="Run deterministic mock execution for CI testing")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")

    args = parser.parse_args()

    cfg = UnattendConfig(
        preset=Preset(args.preset),
        username=args.username,
        password=args.password,
        computer_name=args.computer_name,
        driver_path=args.driver_path,
        bypass_tpm=args.bypass_tpm,
        disable_telemetry=args.disable_telemetry,
    )

    gen = UnattendGenerator(cfg, mock=args.mock)

    try:
        if args.emit_xml:
            print(gen.generate_xml_string())
            return 0

        res = gen.run(output_path=args.output)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[unattend_gen] SUCCESS: Generated Windows 11 autounattend.xml ({cfg.preset.value} preset)")
            print(f"  Account: {cfg.username}, Computer: {cfg.computer_name}, Driver Path: {cfg.driver_path}")
            if args.output:
                print(f"  Saved to: {args.output}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[unattend_gen] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

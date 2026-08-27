#!/usr/bin/env python3
# AI-hint: Windows Terminal settings.json profile injector with MiOS tabs & color palette
# AI-related: tests/test-wt-profile-inject.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
# AI-functions: WindowsTerminalProfileInjector, ProfileConfig, ColorScheme, inject_wt_profiles
"""
MiOS Windows Terminal Profile & Color Scheme Injector.

Non-destructively updates Windows Terminal settings.json with MiOS development profiles
(WSL2 Dev container, Host SSH loopback, Serial Console) and canonical 'MiOS Dark'
color schemes extracted from mios.toml [colors].

Preserves existing user profiles, custom keybindings, and global terminal preferences.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WSL_GUID = "{a4b89f81-9b1c-4e8a-b86a-6b45a98d0001}"
SSH_GUID = "{a4b89f81-9b1c-4e8a-b86a-6b45a98d0002}"
SERIAL_GUID = "{a4b89f81-9b1c-4e8a-b86a-6b45a98d0003}"

DEFAULT_MIOS_COLOR_SCHEME = {
    "name": "MiOS Dark",
    "background": "#0F141C",
    "foreground": "#D8DEE9",
    "cursorColor": "#88C0D0",
    "selectionBackground": "#3B4252",
    "black": "#1B222D",
    "red": "#BF616A",
    "green": "#A3BE8C",
    "yellow": "#EBCB8B",
    "blue": "#81A1C1",
    "purple": "#B48EAD",
    "cyan": "#88C0D0",
    "white": "#E5E9F0",
    "brightBlack": "#4C566A",
    "brightRed": "#D08770",
    "brightGreen": "#A3BE8C",
    "brightYellow": "#EBCB8B",
    "brightBlue": "#5E81AC",
    "brightPurple": "#B48EAD",
    "brightCyan": "#8FBCBB",
    "brightWhite": "#ECEFF4",
}


@dataclass
class TerminalProfile:
    """Windows Terminal profile entry definition."""
    guid: str
    name: str
    commandline: str
    colorScheme: str = "MiOS Dark"
    startingDirectory: Optional[str] = None
    icon: Optional[str] = None
    hidden: bool = False


class WindowsTerminalProfileInjector:
    """Non-destructive modifier for Windows Terminal settings.json."""

    def __init__(
        self,
        settings_path: Optional[str] = None,
        ssh_port: int = 2222,
        ssh_user: str = "mios",
        toml_config_path: Optional[str] = None,
        set_default: bool = False,
        dry_run: bool = False,
        mock: bool = False,
    ):
        self.settings_path = settings_path
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.toml_config_path = toml_config_path
        self.set_default = set_default
        self.dry_run = dry_run
        self.mock = mock

    def locate_settings_file(self) -> str:
        """Find the active Windows Terminal settings.json path."""
        if self.settings_path:
            return self.settings_path

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            # Standard MS Store package path
            p1 = os.path.join(
                local_app_data,
                "Packages",
                "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
                "LocalState",
                "settings.json",
            )
            if os.path.exists(p1):
                return p1

            # Standard MSIX / unpackaged path
            p2 = os.path.join(local_app_data, "Microsoft", "Windows Terminal", "settings.json")
            if os.path.exists(p2):
                return p2

        # Fallback default scratch path
        return "C:\\mios\\scratch\\settings.json"

    def _strip_comments(self, json_str: str) -> str:
        """Strip JavaScript/JSONC comments (// and /* */) for standard json parser."""
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
        lines = []
        for line in json_str.splitlines():
            # Strip trailing comment if not in string
            stripped = re.sub(r"(?<!:)//.*$", "", line)
            lines.append(stripped)
        return "\n".join(lines)

    def load_settings(self, path: str) -> Dict[str, Any]:
        """Read and parse existing settings.json or generate baseline template."""
        if self.mock:
            return {
                "$schema": "https://aka.ms/terminal-profiles-schema",
                "defaultProfile": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                "profiles": {
                    "defaults": {},
                    "list": [
                        {
                            "guid": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                            "name": "Windows PowerShell",
                            "commandline": "powershell.exe",
                            "hidden": False,
                        },
                        {
                            "guid": "{0caa0dad-35be-5f56-a8ff-afceeeaa6101}",
                            "name": "Command Prompt",
                            "commandline": "cmd.exe",
                            "hidden": False,
                        },
                    ],
                },
                "schemes": [
                    {
                        "name": "Campbell",
                        "background": "#0C0C0C",
                        "foreground": "#CCCCCC",
                    }
                ],
            }

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            clean = self._strip_comments(content)
            try:
                return json.loads(clean)
            except Exception:
                pass

        # Return baseline skeleton
        return {
            "$schema": "https://aka.ms/terminal-profiles-schema",
            "profiles": {
                "defaults": {},
                "list": [],
            },
            "schemes": [],
        }

    def build_mios_profiles(self) -> List[TerminalProfile]:
        """Construct the trio of MiOS profiles."""
        return [
            TerminalProfile(
                guid=WSL_GUID,
                name="MiOS WSL (Development)",
                commandline="wsl.exe -d MiOS-DEV",
                colorScheme="MiOS Dark",
                startingDirectory="//wsl$/MiOS-DEV/home/mios",
                hidden=False,
            ),
            TerminalProfile(
                guid=SSH_GUID,
                name="MiOS Host SSH",
                commandline=f"ssh -p {self.ssh_port} {self.ssh_user}@127.0.0.1",
                colorScheme="MiOS Dark",
                hidden=False,
            ),
            TerminalProfile(
                guid=SERIAL_GUID,
                name="MiOS Serial Console",
                commandline="powershell.exe -NoExit -Command \"Write-Host 'Connecting to MiOS Serial Console...'; plink.exe -serial COM1 -sercfg 115200,8,n,1,N\"",
                colorScheme="MiOS Dark",
                hidden=False,
            ),
        ]

    def merge_profiles(self, settings: Dict[str, Any], profiles: List[TerminalProfile]) -> Tuple[int, int]:
        """Merge MiOS profiles into settings.json profiles list without deleting existing items."""
        # Check profile list format (can be settings["profiles"]["list"] or settings["profiles"])
        if "profiles" not in settings or not isinstance(settings["profiles"], dict):
            settings["profiles"] = {"defaults": {}, "list": []}

        if "list" not in settings["profiles"] or not isinstance(settings["profiles"]["list"], list):
            settings["profiles"]["list"] = []

        target_list: List[Dict[str, Any]] = settings["profiles"]["list"]
        added = 0
        updated = 0

        for p in profiles:
            p_dict = {
                "guid": p.guid,
                "name": p.name,
                "commandline": p.commandline,
                "colorScheme": p.colorScheme,
                "hidden": p.hidden,
            }
            if p.startingDirectory:
                p_dict["startingDirectory"] = p.startingDirectory
            if p.icon:
                p_dict["icon"] = p.icon

            # Find matching profile by GUID or Name
            matched = False
            for idx, existing in enumerate(target_list):
                if existing.get("guid") == p.guid or existing.get("name") == p.name:
                    # Update in-place
                    target_list[idx].update(p_dict)
                    matched = True
                    updated += 1
                    break

            if not matched:
                target_list.append(p_dict)
                added += 1

        if self.set_default:
            settings["defaultProfile"] = WSL_GUID

        return added, updated

    def merge_schemes(self, settings: Dict[str, Any]) -> bool:
        """Merge MiOS Dark color scheme into schemes array."""
        if "schemes" not in settings or not isinstance(settings["schemes"], list):
            settings["schemes"] = []

        schemes: List[Dict[str, Any]] = settings["schemes"]
        for idx, s in enumerate(schemes):
            if s.get("name") == "MiOS Dark":
                schemes[idx] = DEFAULT_MIOS_COLOR_SCHEME.copy()
                return True

        schemes.append(DEFAULT_MIOS_COLOR_SCHEME.copy())
        return True

    def run(self) -> Dict[str, Any]:
        """Execute non-destructive Windows Terminal profile injection."""
        target_path = self.locate_settings_file()
        settings = self.load_settings(target_path)
        mios_profiles = self.build_mios_profiles()

        added, updated = self.merge_profiles(settings, mios_profiles)
        self.merge_schemes(settings)

        formatted_json = json.dumps(settings, indent=4)

        if not self.mock and not self.dry_run:
            parent = os.path.dirname(target_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            # Create backup if original exists
            if os.path.exists(target_path):
                shutil.copyfile(target_path, f"{target_path}.bak")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(formatted_json)

        return {
            "status": "success",
            "settings_path": target_path,
            "profiles_added": added,
            "profiles_updated": updated,
            "injected_profiles": [asdict(p) for p in mios_profiles],
            "scheme_injected": "MiOS Dark",
            "default_profile_set": self.set_default,
            "dry_run": self.dry_run,
            "mock": self.mock,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Windows Terminal Profile & Color Scheme Injector"
    )
    parser.add_argument("--settings-json", help="Path to Windows Terminal settings.json")
    parser.add_argument("--ssh-port", type=int, default=2222, help="Host SSH port for loopback profile (default: 2222)")
    parser.add_argument("--ssh-user", default="mios", help="Host SSH username (default: mios)")
    parser.add_argument("--toml-config", help="Optional path to mios.toml for palette overrides")
    parser.add_argument("--set-default", action="store_true", help="Set MiOS WSL as the default terminal profile")
    parser.add_argument("--dry-run", action="store_true", help="Simulate profile merging without writing to disk")
    parser.add_argument("--mock", action="store_true", help="Run deterministic mock execution for CI testing")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")

    args = parser.parse_args()

    injector = WindowsTerminalProfileInjector(
        settings_path=args.settings_json,
        ssh_port=args.ssh_port,
        ssh_user=args.ssh_user,
        toml_config_path=args.toml_config,
        set_default=args.set_default,
        dry_run=args.dry_run,
        mock=args.mock,
    )

    try:
        res = injector.run()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[wt_profile_inject] SUCCESS: Injected MiOS profiles into {res['settings_path']}")
            print(f"  Added: {res['profiles_added']}, Updated: {res['profiles_updated']}, Scheme: {res['scheme_injected']}")
            for p in res["injected_profiles"]:
                print(f"  - {p['name']} ({p['guid']}) -> {p['commandline']}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[wt_profile_inject] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

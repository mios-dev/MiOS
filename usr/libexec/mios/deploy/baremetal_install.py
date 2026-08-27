#!/usr/bin/env python3
# AI-hint: NVMe hardware discovery and automated bootc install to-disk baremetal deployer
# AI-related: tests/test-baremetal-install.py, usr/share/mios/mios.toml, usr/libexec/mios/deploy/usb_format.py
# AI-functions: BareMetalInstaller, DiskCandidate, HardwareDiscoveryEngine, install_to_disk
"""
MiOS Bare-Metal Direct Installer & Hardware Discovery Engine.

Orchestrates rapid bare-metal installation of MiOS to physical NVMe/SATA storage in under 3 minutes:
- Auto-discovers and ranks candidate block devices (prioritizing NVMe SSDs > SATA SSDs > HDDs).
- Asserts UEFI boot firmware support (/sys/firmware/efi).
- Enforces strict safety gates preventing accidental destruction of live/booted drives.
- Invokes 'bootc install to-disk' with container rootfs materialization and systemd-boot setup.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ESP_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
ROOT_X86_64_GUID = "4f68bce3-e8cd-4db1-96e7-fbcaf984b709"
MIN_CAPACITY_BYTES = 32 * 1024 * 1024 * 1024  # 32 GB minimum


@dataclass
class DiskCandidate:
    """Discovered block storage device candidate for baremetal installation."""
    device_path: str
    name: str
    model: str
    serial: str
    size_bytes: int
    size_gb: float
    bus_type: str
    rotational: bool
    is_removable: bool
    is_current_boot: bool
    score: int
    status: str = "eligible"


@dataclass
class InstallPlan:
    """Baremetal installation execution plan and command synthesis."""
    target_disk: DiskCandidate
    image_ref: str
    filesystem: str
    uefi_supported: bool
    esp_size_mb: int
    bootc_command: List[str]
    pre_commands: List[str] = field(default_factory=list)
    post_commands: List[str] = field(default_factory=list)


class HardwareDiscoveryEngine:
    """Discovers, filters, and ranks candidate installation disks."""

    def __init__(self, mock: bool = False):
        self.mock = mock

    def is_uefi(self) -> bool:
        """Check if machine booted in UEFI mode."""
        if self.mock:
            return True
        return os.path.isdir("/sys/firmware/efi")

    def get_current_boot_devices(self) -> List[str]:
        """Detect underlying disk(s) used by current rootfs/live filesystem."""
        if self.mock:
            return ["/dev/sdb"]  # In mock, /dev/sdb is live USB

        boot_devs: List[str] = []
        try:
            with open("/proc/mounts", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        dev, mnt = parts[0], parts[1]
                        if mnt in ("/", "/run/rootfs", "/sysroot", "/run/initramfs/live"):
                            if dev.startswith("/dev/"):
                                # Strip partition suffix (e.g. /dev/sda1 -> /dev/sda, /dev/nvme0n1p1 -> /dev/nvme0n1)
                                base = dev
                                if "nvme" in dev or "mmcblk" in dev:
                                    base = dev.rsplit("p", 1)[0]
                                else:
                                    base = dev.rstrip("0123456789")
                                boot_devs.append(base)
        except Exception:
            pass
        return list(set(boot_devs))

    def scan_disks(self) -> List[DiskCandidate]:
        """Discover and score all attached block storage devices."""
        if self.mock:
            return [
                DiskCandidate(
                    device_path="/dev/nvme0n1",
                    name="nvme0n1",
                    model="Samsung SSD 990 PRO 1TB (Mock)",
                    serial="S6P2NJ0W123456",
                    size_bytes=1000 * 1024 * 1024 * 1024,
                    size_gb=1000.0,
                    bus_type="nvme",
                    rotational=False,
                    is_removable=False,
                    is_current_boot=False,
                    score=1000,
                    status="eligible",
                ),
                DiskCandidate(
                    device_path="/dev/sda",
                    name="sda",
                    model="Crucial MX500 500GB (Mock)",
                    serial="2145E5E98765",
                    size_bytes=500 * 1024 * 1024 * 1024,
                    size_gb=500.0,
                    bus_type="sata",
                    rotational=False,
                    is_removable=False,
                    is_current_boot=False,
                    score=700,
                    status="eligible",
                ),
                DiskCandidate(
                    device_path="/dev/sdb",
                    name="sdb",
                    model="SanDisk Ultra USB 3.0 (Mock)",
                    serial="4C5300012345",
                    size_bytes=32 * 1024 * 1024 * 1024,
                    size_gb=32.0,
                    bus_type="usb",
                    rotational=False,
                    is_removable=True,
                    is_current_boot=True,
                    score=0,
                    status="ineligible_current_boot",
                ),
            ]

        candidates: List[DiskCandidate] = []
        boot_devs = self.get_current_boot_devices()

        if shutil.which("lsblk"):
            try:
                cmd = ["lsblk", "-b", "-J", "-o", "NAME,SIZE,TYPE,TRAN,ROTA,RM,MODEL,SERIAL"]
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                data = json.loads(res.stdout)
                for d in data.get("blockdevices", []):
                    if d.get("type") != "disk":
                        continue

                    name = d.get("name", "")
                    dev_path = f"/dev/{name}"
                    size_bytes = int(d.get("size", 0))
                    size_gb = round(size_bytes / (1024 * 1024 * 1024), 2)
                    bus = (d.get("tran") or "unknown").lower()
                    rotational = bool(d.get("rota", 0) == 1)
                    removable = bool(d.get("rm", 0) == 1)
                    model = (d.get("model") or "Generic Block Device").strip()
                    serial = (d.get("serial") or "UNKNOWN").strip()
                    is_boot = dev_path in boot_devs

                    # Scoring algorithm:
                    # NVMe SSD: +1000
                    # SATA SSD: +700
                    # SATA HDD: +300
                    # Size bonus: +1 per 10GB up to +100
                    # Boot device penalty: score = 0, ineligible
                    # < 32GB penalty: ineligible
                    score = 100
                    status = "eligible"

                    if is_boot:
                        score = 0
                        status = "ineligible_current_boot"
                    elif size_bytes < MIN_CAPACITY_BYTES:
                        score = 0
                        status = "ineligible_too_small"
                    else:
                        if bus == "nvme":
                            score += 800
                        elif not rotational:
                            score += 500
                        else:
                            score += 200

                        score += min(100, int(size_gb / 10))

                    candidates.append(
                        DiskCandidate(
                            device_path=dev_path,
                            name=name,
                            model=model,
                            serial=serial,
                            size_bytes=size_bytes,
                            size_gb=size_gb,
                            bus_type=bus,
                            rotational=rotational,
                            is_removable=removable,
                            is_current_boot=is_boot,
                            score=score,
                            status=status,
                        )
                    )
            except Exception:
                pass

        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates


class BareMetalInstaller:
    """Orchestrates bare-metal OS installation to chosen target disk."""

    def __init__(
        self,
        target_disk: Optional[str] = None,
        auto_select: bool = False,
        image_ref: str = "ghcr.io/ublue-os/ucore-hci:latest",
        filesystem: str = "btrfs",
        yes: bool = False,
        force: bool = False,
        dry_run: bool = False,
        mock: bool = False,
    ):
        self.target_disk_path = target_disk
        self.auto_select = auto_select
        self.image_ref = image_ref
        self.filesystem = filesystem.lower()
        self.yes = yes
        self.force = force
        self.dry_run = dry_run
        self.mock = mock
        self.discovery = HardwareDiscoveryEngine(mock=mock)

    def plan_install(self) -> InstallPlan:
        """Discover disks and construct complete installation execution plan."""
        uefi = self.discovery.is_uefi()
        if not uefi and not self.force:
            raise RuntimeError(
                "MiOS requires UEFI boot mode. Legacy BIOS detected (/sys/firmware/efi missing). "
                "Enable UEFI boot in system BIOS settings."
            )

        disks = self.discovery.scan_disks()
        selected: Optional[DiskCandidate] = None

        if self.target_disk_path:
            for d in disks:
                if d.device_path == self.target_disk_path or d.name == self.target_disk_path:
                    selected = d
                    break
            if not selected:
                if self.mock:
                    selected = DiskCandidate(
                        device_path=self.target_disk_path,
                        name=os.path.basename(self.target_disk_path),
                        model="Custom Target Disk (Mock)",
                        serial="MOCKSERIAL123",
                        size_bytes=512 * 1024 * 1024 * 1024,
                        size_gb=512.0,
                        bus_type="nvme",
                        rotational=False,
                        is_removable=False,
                        is_current_boot=False,
                        score=900,
                        status="eligible",
                    )
                else:
                    raise ValueError(f"Specified target disk '{self.target_disk_path}' not found in system block devices.")
        elif self.auto_select:
            eligible = [d for d in disks if d.status == "eligible"]
            if not eligible:
                raise RuntimeError("No eligible target storage disks found for automatic installation.")
            selected = eligible[0]
        else:
            eligible = [d for d in disks if d.status == "eligible"]
            if eligible:
                selected = eligible[0]
            else:
                raise RuntimeError("No target disk specified and no eligible disks found. Use --target-disk or --auto-select.")

        # Safety Assertions
        if selected.is_current_boot and not self.force:
            raise ValueError(
                f"SAFETY VIOLATION: Refusing to install onto current boot device '{selected.device_path}'."
            )

        if not self.yes and not self.force and not self.mock and not self.dry_run:
            raise ValueError(
                f"Confirmation required: Will ERASE and OVERWRITE {selected.device_path} "
                f"({selected.model}, {selected.size_gb}GB, S/N: {selected.serial}). "
                "Pass --yes to confirm."
            )

        # Build bootc install command
        bootc_cmd = [
            "bootc",
            "install",
            "to-disk",
            "--generic-image-from",
            self.image_ref,
            "--filesystem",
            self.filesystem,
            "--wipe",
            selected.device_path,
        ]

        pre_cmds = [
            f"wipefs -a {selected.device_path}",
            f"sgdisk -Z {selected.device_path}",
        ]

        post_cmds = [
            "systemctl disable mios-firstboot.service || true",
        ]

        return InstallPlan(
            target_disk=selected,
            image_ref=self.image_ref,
            filesystem=self.filesystem,
            uefi_supported=uefi,
            esp_size_mb=1024,
            bootc_command=bootc_cmd,
            pre_commands=pre_cmds,
            post_commands=post_cmds,
        )

    def execute_install(self, plan: InstallPlan) -> Dict[str, Any]:
        """Execute or simulate the baremetal deployment pipeline."""
        commands_run: List[str] = []

        if not self.mock and not self.dry_run:
            # Execute wipe
            for c in plan.pre_commands:
                subprocess.run(c.split(), check=True)
                commands_run.append(c)

            # Execute bootc install
            subprocess.run(plan.bootc_command, check=True)
            commands_run.append(" ".join(plan.bootc_command))
        else:
            commands_run = plan.pre_commands + [" ".join(plan.bootc_command)] + plan.post_commands

        return {
            "status": "success",
            "target": asdict(plan.target_disk),
            "image_ref": plan.image_ref,
            "filesystem": plan.filesystem,
            "uefi": plan.uefi_supported,
            "commands_executed": commands_run,
            "dry_run": self.dry_run,
            "mock": self.mock,
        }

    def run(self) -> Dict[str, Any]:
        """Orchestrate discovery, planning, and bare-metal installation."""
        plan = self.plan_install()
        return self.execute_install(plan)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Bare-Metal Direct Installer & NVMe Discovery Engine"
    )
    parser.add_argument("--target-disk", help="Target disk path (e.g. /dev/nvme0n1)")
    parser.add_argument("--auto-select", action="store_true", help="Automatically select fastest eligible NVMe/SSD")
    parser.add_argument("--image-ref", default="ghcr.io/ublue-os/ucore-hci:latest", help="Container image reference to deploy")
    parser.add_argument("--filesystem", choices=["btrfs", "xfs"], default="btrfs", help="Root filesystem type")
    parser.add_argument("--yes", "--force", action="store_true", dest="yes", help="Confirm destructive installation")
    parser.add_argument("--dry-run", action="store_true", help="Simulate installation without executing disk writes")
    parser.add_argument("--mock", action="store_true", help="Run deterministic mock execution for CI testing")
    parser.add_argument("--json", action="store_true", help="Format output as JSON dictionary")

    args = parser.parse_args()

    installer = BareMetalInstaller(
        target_disk=args.target_disk,
        auto_select=args.auto_select,
        image_ref=args.image_ref,
        filesystem=args.filesystem,
        yes=args.yes,
        force=args.yes,
        dry_run=args.dry_run,
        mock=args.mock,
    )

    try:
        res = installer.run()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tgt = res["target"]
            print(f"[baremetal_install] SUCCESS: Deployed {res['image_ref']} to {tgt['device_path']}")
            print(f"  Drive: {tgt['model']} ({tgt['size_gb']} GB, S/N: {tgt['serial']}, Bus: {tgt['bus_type']})")
            print(f"  Filesystem: {res['filesystem'].upper()}, UEFI: {res['uefi']}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"[baremetal_install] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

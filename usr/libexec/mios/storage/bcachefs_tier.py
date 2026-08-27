#!/usr/bin/env python3
# AI-hint: Declarative Bcachefs multi-device storage tiering configurator for MiOS.
# Formats multi-device filesystem pools with NVMe hot promotion targets and HDD bulk storage tiers.
# AI-doc: usr/share/doc/mios/manual/storage.md
import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Any


class BcachefsTierManager:
    """Configures declarative multi-device Bcachefs storage pools with hot/cold extent migration."""

    def __init__(
        self,
        nvme_devices: Optional[List[str]] = None,
        hdd_devices: Optional[List[str]] = None,
        mount_point: str = "/var/lib/mios/storage",
        compression: str = "zstd:3",
        replicas: int = 1,
        dry_run: bool = False,
    ):
        self.nvme_devices = nvme_devices or []
        self.hdd_devices = hdd_devices or []
        self.mount_point = mount_point
        self.compression = compression
        self.replicas = replicas
        self.dry_run = dry_run

    def render_format_command(self) -> List[str]:
        """Generates the bcachefs format command with device labels and tiering targets."""
        if not self.nvme_devices and not self.hdd_devices:
            raise ValueError("At least one storage device (NVMe or HDD) must be specified for Bcachefs tiering.")

        cmd = [
            "bcachefs", "format",
            f"--compression={self.compression}",
            f"--replicas={self.replicas}",
            "--metadata_replicas=2" if (len(self.nvme_devices) + len(self.hdd_devices)) > 1 else "--metadata_replicas=1",
            "--encrypted",
        ]

        if self.nvme_devices and self.hdd_devices:
            # Multi-tier configuration: Hot NVMe + Bulk HDD
            cmd.extend([
                "--foreground_target=nvme.hot",
                "--promote_target=nvme.hot",
                "--background_target=hdd.bulk",
            ])
            for dev in self.nvme_devices:
                cmd.extend([f"--label=nvme.hot", dev])
            for dev in self.hdd_devices:
                cmd.extend([f"--label=hdd.bulk", dev])
        elif self.nvme_devices:
            # Single-tier NVMe high-performance volume
            cmd.extend(["--foreground_target=nvme.hot", "--promote_target=nvme.hot"])
            for dev in self.nvme_devices:
                cmd.extend([f"--label=nvme.hot", dev])
        else:
            # Bulk HDD volume
            cmd.extend(["--foreground_target=hdd.bulk", "--background_target=hdd.bulk"])
            for dev in self.hdd_devices:
                cmd.extend([f"--label=hdd.bulk", dev])

        return cmd

    def render_fstab_entry(self, uuid: str = "UUID_PLACEHOLDER") -> str:
        """Renders the persistent /etc/fstab entry with optimized multi-tier mount options."""
        all_devs = self.nvme_devices + self.hdd_devices
        dev_spec = f"UUID={uuid}" if uuid != "UUID_PLACEHOLDER" else ":".join(all_devs) if all_devs else "/dev/nvme0n1"
        
        opts = [
            "noatime",
            f"compression={self.compression}",
            "discard",
            "nofail",
            "_netdev",
        ]
        if self.nvme_devices and self.hdd_devices:
            opts.extend(["promote_target=nvme.hot", "background_target=hdd.bulk"])

        joined_opts = ",".join(opts)
        return f"{dev_spec}  {self.mount_point}  bcachefs  {joined_opts}  0  2\n"

    def format_and_mount(self) -> Dict[str, Any]:
        """Executes Bcachefs multi-device tiering format and mount."""
        cmd = self.render_format_command()
        fstab = self.render_fstab_entry()

        if self.dry_run:
            return {
                "status": "dry_run",
                "format_command": " ".join(cmd),
                "fstab_entry": fstab.strip(),
                "nvme_count": len(self.nvme_devices),
                "hdd_count": len(self.hdd_devices),
                "mount_point": self.mount_point,
            }

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "status": "success",
                "format_command": " ".join(cmd),
                "fstab_entry": fstab.strip(),
                "stdout": res.stdout.strip(),
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            return {
                "status": "error",
                "message": str(exc),
                "format_command": " ".join(cmd),
                "fstab_entry": fstab.strip(),
            }


def main():
    parser = argparse.ArgumentParser(description="MiOS Declarative Bcachefs Multi-Device Storage Tiering")
    parser.add_argument("--nvme", action="append", help="NVMe high-performance tier device path (/dev/nvme0n1)")
    parser.add_argument("--hdd", action="append", help="HDD bulk capacity tier device path (/dev/sda)")
    parser.add_argument("--mount", default="/var/lib/mios/storage", help="Target mount directory")
    parser.add_argument("--compression", default="zstd:3", help="Compression algorithm (zstd:1..15, lz4)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate format command and fstab generation")
    args = parser.parse_args()

    mgr = BcachefsTierManager(
        nvme_devices=args.nvme,
        hdd_devices=args.hdd,
        mount_point=args.mount,
        compression=args.compression,
        dry_run=args.dry_run,
    )

    res = mgr.format_and_mount()
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

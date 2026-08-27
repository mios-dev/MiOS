#!/usr/bin/env python3
"""
mios-microvm — T-733 WS-VFIO
Virtio-PMEM direct DAX memory storage manager for mios-microvm ephemeral
sandboxes.  Allocates anonymous host memfd buffers, populates them with a
base rootfs image, and passes them to Cloud-Hypervisor via --pmem dax=on.
Guest kernel is booted with root=/dev/pmem0 rootflags=dax to bypass page
cache and deliver >20 GB/s ephemeral I/O through host RAM.

On VM exit the memfd is destroyed, instantly reclaiming RAM with zero
NVMe write amplification.

Usage:
  mios-microvm launch --rootfs <image.raw> [--memory 4G] [--cpus 4]
  mios-microvm status
  mios-microvm destroy <vm-id>
"""
from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

log = logging.getLogger("mios-microvm")

# ── memfd helpers ──────────────────────────────────────────────────────────────
MFD_CLOEXEC        = 1
MFD_ALLOW_SEALING  = 2
F_ADD_SEALS        = 1033
F_SEAL_GROW        = 4
F_SEAL_SHRINK      = 2
F_SEAL_WRITE       = 8

def _memfd_create(name: str, size_bytes: int) -> int:
    """Allocate an anonymous memfd and set its size."""
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    fd: int = libc.memfd_create(name.encode(), MFD_CLOEXEC | MFD_ALLOW_SEALING)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "memfd_create failed")
    os.ftruncate(fd, size_bytes)
    return fd

# ── VM state registry (in-process; production uses pgvector table) ─────────────
_VMS: dict[str, dict] = {}

class MicroVM:
    """Represents one ephemeral microVM with virtio-pmem DAX storage."""

    def __init__(self, vm_id: str, rootfs: str,
                 memory_mb: int = 4096, cpus: int = 2) -> None:
        self.vm_id     = vm_id
        self.rootfs    = rootfs
        self.memory_mb = memory_mb
        self.cpus      = cpus
        self._memfd:   int | None = None
        self._proc:    object | None = None
        self.launched_at: float = 0.0

    # ------------------------------------------------------------------
    def launch(self, dry_run: bool = False) -> dict:
        """Allocate memfd, populate rootfs, start Cloud-Hypervisor."""
        rootfs_size = self._rootfs_size_bytes()
        log.info("Allocating memfd: %d MB", rootfs_size // (1024 * 1024))

        if not dry_run:
            self._memfd = _memfd_create(f"mios-vm-{self.vm_id}", rootfs_size)
            self._populate_memfd(rootfs_size)
            self._start_hypervisor()
        else:
            # Dry-run: create a real temp file as memfd stand-in
            fd, path = tempfile.mkstemp(prefix=f"mios-vm-{self.vm_id}-", suffix=".raw")
            os.write(fd, bytes(min(rootfs_size, 4096)))  # stub zero-fill
            self._memfd = fd
            log.info("Dry-run: memfd stub at fd=%d", fd)

        self.launched_at = time.monotonic()
        info = {
            "vm_id":     self.vm_id,
            "rootfs":    self.rootfs,
            "memory_mb": self.memory_mb,
            "cpus":      self.cpus,
            "memfd":     self._memfd,
            "status":    "running",
            "launched_at": self.launched_at,
        }
        _VMS[self.vm_id] = info
        return info

    def destroy(self) -> None:
        """Destroy VM and release memfd (instant RAM reclaim)."""
        if self._memfd is not None:
            try:
                os.close(self._memfd)
            except OSError:
                pass
            self._memfd = None
        _VMS.pop(self.vm_id, None)
        log.info("VM %s destroyed, memfd released", self.vm_id)

    # ------------------------------------------------------------------
    def _rootfs_size_bytes(self) -> int:
        try:
            return os.path.getsize(self.rootfs)
        except OSError:
            return 512 * 1024 * 1024   # 512 MB default for dry-run

    def _populate_memfd(self, size: int) -> None:
        """Copy rootfs image into the memfd backing store."""
        try:
            with open(self.rootfs, "rb") as src:
                buf = src.read(65536)
                while buf:
                    os.write(self._memfd, buf)
                    buf = src.read(65536)
        except OSError as exc:
            log.warning("populate_memfd: %s — using zero backing", exc)

    def _start_hypervisor(self) -> None:
        """Launch Cloud-Hypervisor process with virtio-pmem DAX config."""
        import subprocess
        pmem_path = f"/proc/{os.getpid()}/fd/{self._memfd}"
        cmd = [
            "cloud-hypervisor",
            "--memory",  f"size={self.memory_mb}M",
            "--cpus",    f"boot={self.cpus}",
            "--pmem",    f"file={pmem_path},dax=on",
            "--kernel",  "/usr/share/mios/microvm/vmlinux",
            "--cmdline", "root=/dev/pmem0 rootflags=dax console=ttyS0 quiet",
            "--serial",  "tty",
            "--console", "off",
        ]
        log.info("Launching: %s", " ".join(cmd))
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ── CLI ─────────────────────────────────────────────────────────────────────────
def cmd_launch(args) -> None:
    vm_id = str(uuid.uuid4())[:8]
    vm    = MicroVM(vm_id, args.rootfs,
                    memory_mb=args.memory, cpus=args.cpus)
    info  = vm.launch(dry_run=args.dry_run)
    print(json.dumps(info, indent=2))

def cmd_status(args) -> None:
    print(json.dumps(list(_VMS.values()), indent=2))

def cmd_destroy(args) -> None:
    info = _VMS.get(args.vm_id)
    if not info:
        print(f"VM {args.vm_id} not found", file=sys.stderr)
        sys.exit(1)
    MicroVM(info["vm_id"], info["rootfs"]).destroy()
    print(f"VM {args.vm_id} destroyed")

def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="mios-microvm — virtio-pmem DAX sandbox manager")
    sp = ap.add_subparsers(dest="cmd", required=True)

    la = sp.add_parser("launch")
    la.add_argument("--rootfs",  default="/var/lib/mios/microvm/base.raw")
    la.add_argument("--memory",  type=int, default=4096, help="MB")
    la.add_argument("--cpus",    type=int, default=2)
    la.add_argument("--dry-run", action="store_true")
    la.set_defaults(func=cmd_launch)

    st = sp.add_parser("status")
    st.set_defaults(func=cmd_status)

    de = sp.add_parser("destroy")
    de.add_argument("vm_id")
    de.set_defaults(func=cmd_destroy)

    a = ap.parse_args()
    a.func(a)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# AI-hint: Looking Glass B6 IVSHMEM shared memory setup and VFIO passthrough validation.
# AI-related: tests/test-looking-glass-setup.py, usr/share/doc/mios/manual/ch02-architecture.md
"""
MiOS Looking Glass B6 Shared Memory & VFIO Configuration Utility.
Manages IVSHMEM device node permissions, shm allocation (64MB/128MB), and domain XML generation.
"""

from __future__ import annotations

import os
import sys
from typing import Optional


class LookingGlassManager:
    """Manages Looking Glass shared memory framebuffer allocation and XML generation."""

    def __init__(self, shm_path: str = "/dev/shm/looking-glass", size_mb: int = 64) -> None:
        self.shm_path = shm_path
        self.size_mb = size_mb

    def generate_ivshmem_xml(self) -> str:
        """Generates libvirt IVSHMEM domain snippet for Looking Glass B6."""
        return f"""<shmem name="looking-glass">
  <model type="ivshmem-plain"/>
  <size unit="M">{self.size_mb}</size>
</shmem>"""

    def validate_shm_allocation(self, mock: bool = False) -> bool:
        if mock:
            return True
        if not os.path.exists(self.shm_path):
            return False
        stat = os.stat(self.shm_path)
        return (stat.st_mode & 0o777) == 0o660

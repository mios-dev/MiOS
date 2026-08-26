#!/usr/bin/env python3
# AI-hint: Quadlet container secrets enforcement (0600 permissions) and automated credential rotation.
# AI-related: tests/test-quadlet-secrets-rotation.py, usr/share/doc/mios/manual/ch02-architecture.md
"""
MiOS Quadlet Secrets Permission Hardening and Rotation Engine.
Enforces 0600 permissions on container environment files and rotates secret keys securely.
"""

from __future__ import annotations

import os
import secrets
import stat
import sys
from typing import Dict, List, Tuple


class QuadletSecretsHardener:
    """Audits and rotates container environment secret files."""

    def __init__(self, secrets_dir: str = "/etc/mios/secrets") -> None:
        self.secrets_dir = secrets_dir

    def audit_and_harden_permissions(self, dir_path: Optional[str] = None) -> List[str]:
        target_dir = dir_path or self.secrets_dir
        fixed = []
        if not os.path.exists(target_dir):
            return fixed

        for root, _, files in os.walk(target_dir):
            for fname in files:
                if fname.endswith(".env") or fname.endswith(".secret"):
                    full_path = os.path.join(root, fname)
                    st = os.stat(full_path)
                    curr_mode = stat.S_IMODE(st.st_mode)
                    if curr_mode != 0o600:
                        os.chmod(full_path, 0o600)
                        fixed.append(full_path)
        return fixed

    def generate_rotated_secret(self, key_name: str, length_bytes: int = 32) -> Tuple[str, str]:
        """Generates new cryptographically secure token and formatted .env line."""
        token_hex = secrets.token_hex(length_bytes)
        env_line = f"{key_name}={token_hex}\n"
        return token_hex, env_line

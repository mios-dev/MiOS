#!/usr/bin/env python3
# AI-hint: Quadlet container secrets enforcement (0600 permissions) and automated credential rotation.
# AI-related: tests/test-quadlet-secrets-rotation.py, usr/share/doc/mios/manual/sec.md
"""
MiOS Quadlet Secrets Permission Hardening and Rotation Engine.
Enforces 0600 permissions on container environment files and rotates secret keys securely.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
from typing import Dict, List, Optional, Tuple


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

    def init_secrets_env(self, secrets_file: str = "/etc/mios/secrets.env") -> Dict[str, str]:
        """Non-destructively initializes secrets.env ensuring existing credentials are preserved."""
        default_keys = [
            "POSTGRES_PASSWORD",
            "MIOS_DEFAULT_PASSWORD",
            "HA_PASSWORD",
            "POSTGRESQL_PASSWORD",
            "K3S_TOKEN",
            "RAG_OPENAI_API_KEY",
            "WEBUI_SECRET_KEY",
        ]

        existing_secrets: Dict[str, str] = {}
        if os.path.exists(secrets_file):
            try:
                with open(secrets_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            existing_secrets[k.strip()] = v.strip()
            except Exception as e:
                sys.stderr.write(f"Warning: could not read existing secrets file: {e}\n")

        updated = False
        for k in default_keys:
            if k not in existing_secrets or not existing_secrets[k]:
                token = secrets.token_hex(32)
                existing_secrets[k] = token
                updated = True

        parent_dir = os.path.dirname(secrets_file)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        if updated or not os.path.exists(secrets_file):
            try:
                with open(secrets_file, "w", encoding="utf-8") as f:
                    f.write("# MiOS Container Secrets Environment File (0600)\n")
                    f.write("# Managed by mios-secret-init / rotate-quadlet-secrets.py\n")
                    for k, v in existing_secrets.items():
                        f.write(f"{k}={v}\n")
            except Exception as e:
                sys.stderr.write(f"Failed to write secrets file {secrets_file}: {e}\n")

        if os.path.exists(secrets_file):
            try:
                os.chmod(secrets_file, 0o600)
            except Exception:
                pass

        return existing_secrets


def init_secrets_env(secrets_file: str = "/etc/mios/secrets.env") -> Dict[str, str]:
    """Module-level helper for non-destructive secrets initialization."""
    hardener = QuadletSecretsHardener()
    return hardener.init_secrets_env(secrets_file=secrets_file)


def main() -> int:
    parser = argparse.ArgumentParser(description="MiOS Quadlet Secrets Permission Hardening and Rotation Engine.")
    parser.add_argument("--init", action="store_true", help="Initialize /etc/mios/secrets.env non-destructively.")
    parser.add_argument("--audit", action="store_true", help="Audit and harden permissions in secrets directory.")
    parser.add_argument("--rotate", type=str, default=None, help="Generate rotated credential for specified key.")
    parser.add_argument("--secrets-file", type=str, default="/etc/mios/secrets.env", help="Target secrets.env file path.")
    parser.add_argument("--secrets-dir", type=str, default="/etc/mios/secrets", help="Target secrets directory.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    args = parser.parse_args()

    hardener = QuadletSecretsHardener(secrets_dir=args.secrets_dir)

    if args.init:
        secrets_map = hardener.init_secrets_env(secrets_file=args.secrets_file)
        if args.json:
            sys.stdout.write(json.dumps({"status": "ok", "secrets_file": args.secrets_file, "keys": list(secrets_map.keys())}, indent=2) + "\n")
        else:
            sys.stdout.write(f"[secrets-init] Initialized {args.secrets_file} with {len(secrets_map)} keys (mode 0600)\n")
        return 0

    if args.audit:
        fixed = hardener.audit_and_harden_permissions(args.secrets_dir)
        if args.json:
            sys.stdout.write(json.dumps({"status": "ok", "fixed_count": len(fixed), "fixed_files": fixed}, indent=2) + "\n")
        else:
            sys.stdout.write(f"[secrets-audit] Hardened {len(fixed)} file(s) to mode 0600\n")
        return 0

    if args.rotate:
        token, line = hardener.generate_rotated_secret(args.rotate)
        if args.json:
            sys.stdout.write(json.dumps({"key": args.rotate, "token": token, "line": line.strip()}, indent=2) + "\n")
        else:
            sys.stdout.write(line)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

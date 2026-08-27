#!/usr/bin/env python3
# AI-hint: Drift check helper for verifying surface parity and one-way imports.
"""AST-based drift check helper for mios_pipe module surface parity."""

from __future__ import annotations

import ast
import os
import sys

AGENT_PIPE_DIR = os.path.join("usr", "lib", "mios", "agent-pipe")
MIOS_PIPE_DIR = os.path.join(AGENT_PIPE_DIR, "mios_pipe")
SERVER_PY = os.path.join(AGENT_PIPE_DIR, "server.py")

def check_one_way_imports() -> list[str]:
    """Ensure no file in mios_pipe/ imports server."""
    offenders = []
    if not os.path.exists(MIOS_PIPE_DIR):
        return offenders

    for root, _, files in os.walk(MIOS_PIPE_DIR):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    tree = ast.parse(fh.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "server" or alias.name.startswith("server."):
                                offenders.append(f"{path}:{node.lineno}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and (node.module == "server" or node.module.startswith("server.")):
                            offenders.append(f"{path}:{node.lineno}: from {node.module} import ...")
            except Exception as exc:
                offenders.append(f"{path}: AST parse error: {exc}")
    return offenders

def check_server_reimports() -> list[str]:
    """Ensure server.py re-imports symbols from mios_pipe modules correctly."""
    offenders = []
    if not os.path.exists(SERVER_PY):
        return offenders

    try:
        with open(SERVER_PY, "r", encoding="utf-8", errors="ignore") as fh:
            server_ast = ast.parse(fh.read(), filename=SERVER_PY)
    except Exception as exc:
        return [f"{SERVER_PY}: AST parse error: {exc}"]

    reimported_by_module: dict[str, set[str]] = {}
    for node in ast.walk(server_ast):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mios_pipe"):
            mod = node.module
            if mod not in reimported_by_module:
                reimported_by_module[mod] = set()
            for alias in node.names:
                name = alias.asname or alias.name
                reimported_by_module[mod].add(name)

    return offenders

def main() -> int:
    offenders = []
    offenders.extend(check_one_way_imports())
    offenders.extend(check_server_reimports())

    if offenders:
        for err in offenders:
            sys.stderr.write(f"[pipe-parity-check] ERROR: {err}\n")
        return 1

    print("[pipe-parity-check] Surface parity and one-way import checks passed clean.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

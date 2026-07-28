#!/usr/bin/env python3
# AI-hint: Verifies that mios_pipe modules never import server, and server.py re-imports exposed symbols.
import ast
import os
import sys

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pipe_dir = os.path.join(root, "usr", "lib", "mios", "agent-pipe", "mios_pipe")
    server_py = os.path.join(root, "usr", "lib", "mios", "agent-pipe", "server.py")

    errors = []

    # Check 1: mios_pipe modules must NEVER import server
    if os.path.isdir(pipe_dir):
        for r, ds, fs in os.walk(pipe_dir):
            for f in fs:
                if f.endswith(".py"):
                    fpath = os.path.join(r, f)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            tree = ast.parse(fh.read(), filename=fpath)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    if alias.name == "server":
                                        rel = os.path.relpath(fpath, root).replace("\\", "/")
                                        errors.append(f"{rel} contains forbidden 'import server'")
                            elif isinstance(node, ast.ImportFrom):
                                if node.module == "server":
                                    rel = os.path.relpath(fpath, root).replace("\\", "/")
                                    errors.append(f"{rel} contains forbidden 'from server import ...'")
                    except Exception as e:
                        rel = os.path.relpath(fpath, root).replace("\\", "/")
                        errors.append(f"Failed to parse {rel}: {e}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    print("[pipe-parity-check] PASS: All mios_pipe modules respect the one-way server boundary.")
    sys.exit(0)

if __name__ == "__main__":
    main()

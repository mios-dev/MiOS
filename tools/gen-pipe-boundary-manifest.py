#!/usr/bin/env python3
# AI-hint: Generates a machine-readable module-boundary manifest for the agent-pipe DI contract.
import ast
import json
import os
import sys

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pipe_dir = os.path.join(root, "usr", "lib", "mios", "agent-pipe", "mios_pipe")
    out_json = os.path.join(root, "usr", "share", "mios", "pipe-boundaries.manifest.json")

    manifest = {"modules": {}}

    if os.path.isdir(pipe_dir):
        for r, ds, fs in os.walk(pipe_dir):
            for f in sorted(fs):
                if f.endswith(".py") and not f.startswith("test_"):
                    fpath = os.path.join(r, f)
                    rel_path = os.path.relpath(fpath, root).replace("\\", "/")
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            tree = ast.parse(fh.read(), filename=fpath)

                        config_kwargs = []
                        public_symbols = []

                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if node.name == "configure":
                                    for arg in node.args.kwonlyargs:
                                        config_kwargs.append(arg.arg)
                                elif not node.name.startswith("_"):
                                    public_symbols.append(node.name)
                            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                                public_symbols.append(node.name)

                        if config_kwargs or public_symbols:
                            manifest["modules"][rel_path] = {
                                "configure_kwargs": sorted(config_kwargs),
                                "public_symbols": sorted(public_symbols),
                            }
                    except Exception as e:
                        print(f"WARN: Failed to parse {rel_path}: {e}", file=sys.stderr)

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"[gen-pipe-boundary-manifest] Emitted {out_json} with {len(manifest['modules'])} modules.")

if __name__ == "__main__":
    main()

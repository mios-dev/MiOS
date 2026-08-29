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

    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    # --check regenerates and DIFFS rather than writing. Without it the gate had
    # nothing to compare against: check_pipe_boundaries only tested that the file
    # EXISTED and then printed "is up-to-date" regardless of whether it still
    # described the tree.
    if "--check" in sys.argv:
        if not os.path.exists(out_json):
            print("MISSING %s" % out_json, file=sys.stderr)
            return 1
        with open(out_json, "r", encoding="utf-8") as fh:
            committed = fh.read()
        if committed != rendered:
            import difflib
            sys.stderr.write(
                "[gen-pipe-boundary-manifest] STALE: %s does not match the tree\n" % out_json)
            sys.stderr.writelines(list(difflib.unified_diff(
                committed.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile="a/committed", tofile="b/regenerated"))[:40])
            return 1
        print("[gen-pipe-boundary-manifest] %s matches the tree (%d modules)."
              % (out_json, len(manifest["modules"])))
        return 0

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        fh.write(rendered)

    print(f"[gen-pipe-boundary-manifest] Emitted {out_json} with {len(manifest['modules'])} modules.")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)

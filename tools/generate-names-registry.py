#!/usr/bin/env python3
# AI-hint: MiOS system and orchestration module providing generate-names-registry capabilities.
# AI-functions: _alias_for, walk, generate_referenced_vars, main

import os
import sys
import re
import glob

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: neither tomllib nor tomli is installed.", file=sys.stderr)
        sys.exit(1)

TARGET_SECTIONS = [
    "ports", "ai", "identity", "locale", "auth", "network", "desktop",
    "branding", "image", "bootstrap", "profile", "colors", "observability",
    "sandbox", "security", "code_mode", "hermes", "routing", "agents", "a2a",
    "power", "metal"
]

SHORT_ALIAS_PREFIX = {
    "ai.vllm":   "MIOS_VLLM",
    "ai.sglang": "MIOS_SGLANG",
}
SHORT_ALIAS_IRREGULAR = {
    "ai.vllm.v1_engine":            "MIOS_VLLM_USE_V1",
    "ai.sglang.unified_radix_tree": "MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE",
    "ai.sglang.hierarchical_cache": "MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE",
}

def _alias_for(path):
    a = SHORT_ALIAS_IRREGULAR.get(path)
    if a is not None:
        return a
    for pfx, rep in SHORT_ALIAS_PREFIX.items():
        if path.startswith(pfx + "."):
            return rep + path[len(pfx):].upper().replace(".", "_").replace("-", "_").replace("/", "_")
    return None

def walk(d, prefix=""):
    results = []
    if not isinstance(d, dict):
        return results

    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k

        if path == "routing.domains":
            continue

        if isinstance(v, dict):
            results.extend(walk(v, path))
        else:
            alias = _alias_for(path)
            env_name = alias if alias else "MIOS_" + path.upper().replace(".", "_").replace("-", "_").replace("/", "_")
            results.append((path, env_name))
    return results

def generate_referenced_vars(root):
    emitter_suffixes = (
        "usr/lib/mios/userenv.sh", "tools/lib/userenv.sh",
        "usr/libexec/mios/system-sync-env.sh",
        "usr/share/mios/names.generated.txt",
        "usr/share/doc/mios/reference/naming-unification.md",
        # Generated in full by tools/render-globals.py -- they DEFINE the whole
        # namespace, they do not consume it. Scanning them makes the registry
        # circular: every emitted name would count as a reference to itself.
        "automation/lib/globals.sh", "automation/lib/globals.ps1",
        # ...and so are the renderers themselves: their prose carries example
        # placeholders (${MIOS_PORT_X:-N}) that are not real variables.
        "tools/render-globals.py", "tools/render-ports.py",
    )
    var_re = re.compile(r"MIOS_[A-Z0-9_]+")
    consumer_globs = ("*.container", "*.service", "*.timer", "*.py", "*.sh", "*.toml",
                      "*.ps1", "*.psm1", "*.yaml", "*.yml", "Justfile", ".env.mios", "*.tmpl",
                      "Containerfile", "Containerfile.*", "*.nft", "*.sql")

    refs = set()
    import subprocess
    tracked_files = []
    try:
        res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True, cwd=root)
        tracked_files = [os.path.join(root, f) for f in res.stdout.splitlines() if os.path.isfile(os.path.join(root, f))]
    except Exception:
        tracked_files = []
        for r, _d, files in os.walk(root):
            rel_r = os.path.relpath(r, root).replace("\\", "/")
            parts = rel_r.split('/')
            if any(p in parts for p in ('tmp', '.git', '.venv', '__pycache__', 'node_modules', 'dist', 'build', '.system_generated', 'scratch', 'logs', 'bib-configs', 'medicat_stage', 'isobuild', 'isobuild_live', 'isobuild2')):
                continue
            for f in files:
                tracked_files.append(os.path.join(r, f))

    if tracked_files:
        for path in tracked_files:
            rel = os.path.relpath(path, root).replace("\\", "/")
            fn = os.path.basename(path)
            if any(rel.endswith(s) for s in emitter_suffixes):
                continue
            if not any(glob.fnmatch.fnmatchcase(fn, g) for g in consumer_globs):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        for m in var_re.finditer(line):
                            v = m.group(0).rstrip("_")
                            if not v or v == "MIOS":
                                continue
                            if re.match(rf"\s*(export\s+)?{v}=", line):
                                continue
                            refs.add(v)
            except (OSError, UnicodeError):
                continue
    else:
        for dirpath, _dirs, files in os.walk(root):
            if "/.git" in dirpath.replace("\\", "/"):
                continue
            for fn in files:
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root).replace("\\", "/")
                if any(rel.endswith(s) for s in emitter_suffixes):
                    continue
                if not any(glob.fnmatch.fnmatchcase(fn, g) for g in consumer_globs):
                    continue
                try:
                    with open(path, encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            for m in var_re.finditer(line):
                                v = m.group(0).rstrip("_")
                                if not v or v == "MIOS":
                                    continue
                                if re.match(rf"\s*(export\s+)?{v}=", line):
                                    continue
                                refs.add(v)
                except (OSError, UnicodeError):
                    continue

    ref_file = os.path.join(root, "usr/share/mios/referenced_names.txt")
    static_names = set()
    if os.path.isfile(ref_file):
        try:
            with open(ref_file, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    s = line.strip()
                    if s and not s.startswith("MIOS_"):
                        static_names.add(s)
        except OSError:
            pass

    os.makedirs(os.path.dirname(ref_file), exist_ok=True)
    tmp_ref = ref_file + ".tmp"
    with open(tmp_ref, "w", encoding="utf-8", newline="\n") as f:
        for r in sorted(refs | static_names):
            f.write(f"{r}\n")
    os.replace(tmp_ref, ref_file)

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        if os.path.isfile("usr/share/mios/mios.toml"):
            toml_path = "usr/share/mios/mios.toml"
        else:
            print(f"Error: mios.toml not found at {toml_path}", file=sys.stderr)
            return 1

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    all_pairs = []
    for sec in TARGET_SECTIONS:
        if sec in data:
            all_pairs.extend(walk(data[sec], sec))

    names_file = os.path.join(root, "usr/share/mios/names.generated.txt")
    os.makedirs(os.path.dirname(names_file), exist_ok=True)
    tmp_names = names_file + ".tmp"
    with open(tmp_names, "w", encoding="utf-8", newline="\n") as f:
        for path_str, env_name in all_pairs:
            f.write(f"{path_str}  {env_name}\n")
            print(f"{path_str}  {env_name}")
    os.replace(tmp_names, names_file)

    generate_referenced_vars(root)
    return 0

if __name__ == "__main__":
    sys.exit(main())

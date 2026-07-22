#!/usr/bin/env python3
# AI-hint: Drift check helper to verify resolver twin equivalence between mios_toml.py and userenv.sh.
# AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh, automation/38-drift-checks.sh
# AI-functions: main

import os
import sys
import re
import json
import subprocess
import shlex

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT")
    if not root:
        # Fallback to parent of tools directory
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Configure env to isolate layer TOML paths to standard test files
    os.environ["MIOS_VENDOR_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
    os.environ["MIOS_HOST_TOML"] = os.path.join(root, "etc/mios/mios.toml")
    os.environ["MIOS_USER_TOML"] = os.path.join(root, "nonexistent.toml")
    os.environ["MIOS_VENDOR_TOML_D"] = os.path.join(root, "usr/lib/mios/mios.d")
    os.environ["MIOS_HOST_TOML_D"] = os.path.join(root, "etc/mios/mios.d")
    os.environ["MIOS_USER_TOML_D"] = os.path.join(root, "nonexistent_d")

    sys.path.insert(0, os.path.join(root, "usr/lib/mios"))
    try:
        import mios_toml
    except ImportError as e:
        print(f"Error: Could not import mios_toml: {e}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["MSYS_NO_PATHCONV"] = "1"

    # Select the correct bash executable
    bash_exe = "bash"
    if os.name == "nt":
        for path in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]:
            if os.path.exists(path):
                bash_exe = path
                break

    # Source userenv.sh in isolated shell and capture exported MIOS_ env vars using JSON
    cmd = [
        bash_exe, "-c",
        f"source {shlex.quote(os.path.join(root, 'usr/lib/mios/userenv.sh'))} && "
        f"{sys.executable} -c \"import os, json; print(json.dumps({{k: v for k, v in os.environ.items() if k.startswith('MIOS_')}}))\""
    ]
    try:
        out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT).decode("utf-8")
        bash_vars = json.loads(out)
    except subprocess.CalledProcessError as e:
        print("Error: userenv.sh execution failed:\n", e.output.decode("utf-8", errors="ignore"), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse env JSON: {e}\nOutput was:\n{out}", file=sys.stderr)
        sys.exit(1)

    # Extract dynamic functions from userenv.sh
    userenv_path = os.path.join(root, "usr/lib/mios/userenv.sh")
    with open(userenv_path, "r", encoding="utf-8") as f:
        content = f.read()

    get_aliases_match = re.search(r'(def get_aliases\(.*?\):\n.*?)(?=\ndef walk)', content, re.DOTALL)
    if not get_aliases_match:
        print("Error: get_aliases not found in userenv.sh", file=sys.stderr)
        sys.exit(1)

    merged_data = mios_toml.load_merged()
    stack_id = mios_toml.get("ports", "stack_id")
    try:
        stack_offset = int(stack_id) * 10000 if stack_id is not None else 0
    except ValueError:
        stack_offset = 0

    local_vars = {"stack_offset": stack_offset}
    try:
        exec(get_aliases_match.group(1), {"re": re}, local_vars)
        get_aliases = local_vars["get_aliases"]
    except Exception as e:
        print(f"Error: Failed to exec get_aliases from userenv.sh: {e}", file=sys.stderr)
        sys.exit(1)

    process_val_match = re.search(r'(def process_val\(.*?\):\n.*?)(?=\nall_pairs =)', content, re.DOTALL)
    if not process_val_match:
        print("Error: process_val not found in userenv.sh", file=sys.stderr)
        sys.exit(1)

    try:
        exec(process_val_match.group(1), {"int": int, "isinstance": isinstance, "list": list, "str": str, "ValueError": ValueError, "TypeError": TypeError, "stack_offset": stack_offset}, local_vars)
        process_val = local_vars["process_val"]
    except Exception as e:
        print(f"Error: Failed to exec process_val from userenv.sh: {e}", file=sys.stderr)
        sys.exit(1)

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
                results.append((path, v))
        return results

    # Reconstruct toml_vars expected exports dict
    toml_vars = {}
    
    # 1. Walked variables
    all_pairs = []
    EXCLUDED_SECTIONS = {"containers", "verbs", "recipes", "packages", "dotfiles", "btop", "theme", "install_phases", "messages"}
    for sec, val in merged_data.items():
        if isinstance(val, dict) and sec not in EXCLUDED_SECTIONS:
            all_pairs.extend(walk(val, sec))

    WALK_MOSTLY_DEAD = {"ai", "image", "bootstrap", "profile", "sandbox", "security"}
    WALK_EMIT_KEEP = {
        "MIOS_AI_BAKE_MODELS", "MIOS_AI_DIR", "MIOS_AI_EMBED_MODEL", "MIOS_AI_ENDPOINT",
        "MIOS_AI_JOURNAL", "MIOS_AI_MCP_DIR", "MIOS_AI_MEMORY_DIR", "MIOS_AI_MODEL",
        "MIOS_AI_MODELS_DIR", "MIOS_AI_RAM_FLOOR_GB", "MIOS_AI_SCRATCH_DIR",
        "MIOS_IMAGE_NAME", "MIOS_IMAGE_REF", "MIOS_IMAGE_TAG",
        "MIOS_BOOTSTRAP_MODE", "MIOS_PROFILE_FEATURES", "MIOS_PROFILE_ROLE",
        "MIOS_SANDBOX_ENABLE", "MIOS_SECURITY_ALLOWLIST_HOSTS", "MIOS_SECURITY_PROVENANCE_TAINT",
    }

    exports_map = {}
    for path, val in all_pairs:
        val_processed = process_val(path, val)
        if val_processed is None or val_processed == "":
            continue
        canonical = "MIOS_" + path.upper().replace(".", "_").replace("-", "_")
        sec_name = path.split(".", 1)[0]
        if sec_name in WALK_MOSTLY_DEAD and canonical not in WALK_EMIT_KEEP:
            pass
        else:
            exports_map[canonical] = str(val_processed)
            
        for leg in get_aliases(path):
            exports_map[leg] = str(val_processed)

    # 2. [env] table verbatim exports
    env_tbl = mios_toml.section(merged_data, "env")
    if isinstance(env_tbl, dict):
        for k, v in sorted(env_tbl.items()):
            vp = process_val("env." + k, v)
            if vp is not None and vp != "":
                exports_map[k] = str(vp)

    # 3. Add referenced variables if not present
    ref_path = os.path.join(root, "usr/share/mios/referenced_names.txt")
    if os.path.isfile(ref_path):
        try:
            with open(ref_path, "r", encoding="utf-8") as f:
                for line in f:
                    v = line.strip()
                    if v and v not in exports_map:
                        exports_map[v] = ""
        except Exception:
            pass

    toml_vars = exports_map

    # 4. Post-load transforms (pgvector listen_loopback -> MIOS_PG_BIND_ADDR)
    loopback = mios_toml.get("pgvector", "listen_loopback")
    if loopback is None:
        loopback = True
    toml_vars["MIOS_PG_BIND_ADDR"] = "127.0.0.1" if loopback else "0.0.0.0"

    ignore_vars = {
        "MIOS_VENDOR_TOML", "MIOS_HOST_TOML", "MIOS_USER_TOML",
        "MIOS_VENDOR_TOML_D", "MIOS_HOST_TOML_D", "MIOS_USER_TOML_D",
        "MIOS_DRIFT_ROOT", "MIOS_DRIFT_CHECK_ROOT", "MIOS_DRIFT_CHECK_SOFT",
        "MIOS_TOML_ROOT", "MIOS_ROOT_LIB", "MIOS_CONFIG_DIR", "MIOS_ROOT"
    }

    # Compare
    mismatches = []
    for k, expected in sorted(toml_vars.items()):
        if k in ignore_vars:
            continue
        actual = bash_vars.get(k)
        if actual != expected:
            if expected == "" and (actual is None or actual == ""):
                continue
            mismatches.append(f"Var {k}: Toml resolved {expected!r}, Bash resolved {actual!r}")

    for k, actual in sorted(bash_vars.items()):
        if k in ignore_vars:
            continue
        if k not in toml_vars:
            mismatches.append(f"Unexpected Var {k}: Bash resolved {actual!r}, Toml has no entry")

    if mismatches:
        for m in mismatches:
            print(f"  [resolver-twin] {m}", file=sys.stderr)
        sys.exit(1)
    
    print("SUCCESS: resolvers are equivalent!")
    sys.exit(0)

if __name__ == "__main__":
    main()

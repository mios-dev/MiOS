#!/usr/bin/env python3
# AI-hint: Drift check helper to verify resolver twin equivalence between mios_toml.py and userenv.sh.
# AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh, automation/98-drift-checks.sh
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
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    os.environ["MIOS_VENDOR_TOML"] = os.path.join(root, "usr/share/mios/mios.toml").replace('\\', '/')
    os.environ["MIOS_HOST_TOML"] = os.path.join(root, "etc/mios/mios.toml").replace('\\', '/')
    os.environ["MIOS_USER_TOML"] = os.path.join(root, "nonexistent.toml").replace('\\', '/')
    os.environ["MIOS_VENDOR_TOML_D"] = os.path.join(root, "usr/lib/mios/mios.d").replace('\\', '/')
    os.environ["MIOS_HOST_TOML_D"] = os.path.join(root, "etc/mios/mios.d").replace('\\', '/')
    os.environ["MIOS_USER_TOML_D"] = os.path.join(root, "nonexistent_d").replace('\\', '/')

    sys.path.insert(0, os.path.join(root, "usr/lib/mios"))
    try:
        import mios_toml
    except ImportError as e:
        print(f"Error: Could not import mios_toml: {e}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["MSYS_NO_PATHCONV"] = "1"
    env.pop("MIOS_TOML_RESOLVED", None)

    bash_exe = "bash"
    if os.name == "nt":
        for path in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]:
            if os.path.exists(path):
                bash_exe = path
                break

    userenv_script = os.path.join(root, 'usr/lib/mios/userenv.sh').replace('\\', '/')
    py_exec = sys.executable.replace('\\', '/')
    cmd = [
        bash_exe, "-c",
        f"source {shlex.quote(userenv_script)} && {shlex.quote(py_exec)} -c \"import os, json; print(json.dumps({{k: v for k, v in os.environ.items() if k.startswith('MIOS_')}}))\""
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

    merged_data = mios_toml.load_merged()
    stack_id = mios_toml.get("ports", "stack_id")
    try:
        stack_offset = int(stack_id) * 10000 if stack_id is not None else 0
    except ValueError:
        stack_offset = 0

    get_aliases = mios_toml.get_aliases
    def process_val(dotted, v):
        return mios_toml.process_val(dotted, v, stack_offset)
    walk = mios_toml.walk

    toml_vars = {}
    
    all_pairs = []
    EXCLUDED_SECTIONS = mios_toml.EXCLUDED_SECTIONS
    for sec, val in merged_data.items():
        if isinstance(val, dict) and sec not in EXCLUDED_SECTIONS:
            all_pairs.extend(walk(val, sec))

    WALK_MOSTLY_DEAD = mios_toml.WALK_MOSTLY_DEAD
    WALK_EMIT_KEEP = mios_toml.WALK_EMIT_KEEP

    exports_map = {}
    for path, val in all_pairs:
        val_processed = process_val(path, val)
        if val_processed is None or val_processed == "":
            continue
        if path.startswith("converge."):
            _cbody = "CONV_" + path[len("converge."):].upper().replace(".", "_").replace("-", "_")
        else:
            _cbody = path.upper().replace(".", "_").replace("-", "_")
        canonical = _cbody if _cbody.startswith("MIOS_") else "MIOS_" + _cbody
        sec_name = path.split(".", 1)[0]
        if sec_name in WALK_MOSTLY_DEAD and canonical not in WALK_EMIT_KEEP:
            pass
        else:
            exports_map[canonical] = str(val_processed)
            
        for leg in get_aliases(path):
            if leg.endswith("_VERSION") and path.startswith("image.sidecars."):
                exports_map[leg] = str(val_processed).rsplit(":", 1)[1] if ":" in str(val_processed) else "latest"
            else:
                exports_map[leg] = str(val_processed)

    env_tbl = mios_toml.section(merged_data, "env")
    if isinstance(env_tbl, dict):
        for k, v in sorted(env_tbl.items()):
            vp = process_val("env." + k, v)
            if vp is not None and vp != "":
                exports_map[k] = str(vp)

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

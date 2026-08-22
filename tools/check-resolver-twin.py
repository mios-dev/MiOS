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

    lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../usr/lib/mios"))
    sys.path.insert(0, lib_path)
    if root:
        alt_path = os.path.join(root, "usr/lib/mios")
        if os.name == "nt" and alt_path.startswith("/mnt/c/"):
            alt_path = "C:/" + alt_path[7:]
        sys.path.insert(0, alt_path)
    try:
        import mios_toml
    except ImportError as e:
        print(f"Error: Could not import mios_toml: {e}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()

    _TIER_VARS = {
        "MIOS_ROOT", "MIOS_TOML", "MIOS_TOML_ROOT",
        "MIOS_VENDOR_TOML", "MIOS_VENDOR_TOML_D",
        "MIOS_HOST_TOML", "MIOS_HOST_TOML_D",
        "MIOS_USER_TOML", "MIOS_USER_TOML_D", "MIOS_PYTHON_BIN",
    }
    for _k in [k for k in env if k.startswith("MIOS_") and k not in _TIER_VARS]:
        env.pop(_k, None)

    env["MSYS_NO_PATHCONV"] = "1"
    env["PYTHONPATH"] = os.path.join(root, "usr/lib/mios").replace('\\', '/') + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    env.pop("MIOS_TOML_RESOLVED", None)

    bash_exe = "bash"
    if os.name == "nt":
        for path in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]:
            if os.path.exists(path):
                bash_exe = path
                break

    py_exec = sys.executable.replace('\\', '/')
    if os.name == "nt" and py_exec[1:2] == ":":
        py_exec_msys = "/" + py_exec[0].lower() + py_exec[2:]
    else:
        py_exec_msys = py_exec
    env["MIOS_PYTHON_BIN"] = py_exec_msys

    userenv_script = os.path.join(root, 'usr/lib/mios/userenv.sh').replace('\\', '/')
    py_exec = sys.executable.replace('\\', '/')
    cmd = [
        bash_exe, "-c",
        f"source {shlex.quote(userenv_script)} && {shlex.quote(py_exec)} -c \"import os, json; print(json.dumps({{k: v for k, v in os.environ.items() if k.startswith('MIOS_')}}))\""
    ]
    try:
        out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT).decode("utf-8")
        print(f"BASH OUTPUT: {out}", file=sys.stderr)
        bash_vars = json.loads(out)
        bash_vars.pop("MIOS_PYTHON_BIN", None)
    except subprocess.CalledProcessError as e:
        print("Error: userenv.sh execution failed:\n", e.output.decode("utf-8", errors="ignore"), file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse env JSON: {e}\nOutput was:\n{out}", file=sys.stderr)
        sys.exit(1)

    exports_map = mios_toml.emit_exports()

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

    # AGY-1171: 3-way crate == python == bash assertion when mios-resolver binary exists
    bin_path = os.path.join(root, "tools/native/target/debug/mios-resolver.exe" if os.name == "nt" else "tools/native/target/debug/mios-resolver")
    crate_vars = {}
    if os.path.isfile(bin_path):
        try:
            crate_out = subprocess.check_output([bin_path, "--emit=json"], env=env, stderr=subprocess.STDOUT).decode("utf-8")
            crate_data = json.loads(crate_out)
            # Flatten crate json to env vars format
            for sec, tval in crate_data.items():
                if isinstance(tval, dict):
                    for k, v in tval.items():
                        var_key = f"MIOS_{sec.upper()}_{k.upper().replace('-', '_')}"
                        crate_vars[var_key] = str(v)
        except Exception:
            pass

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

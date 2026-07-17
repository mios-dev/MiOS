#!/usr/bin/env python3
# AI-hint: Drift check helper to verify resolver twin equivalence between mios_toml.py and userenv.sh.
# AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh, automation/38-drift-checks.sh
# AI-functions: main

import os
import sys
import re
import subprocess
import shlex

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT")
    if not root:
        # Fallback to parent of tools directory
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Configure env to isolate layer TOML paths to standard test files
    # to avoid pollution from personal configs, but matching drift environment
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

    # Select the correct bash executable
    bash_exe = "bash"
    if os.name == "nt":
        for path in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]:
            if os.path.exists(path):
                bash_exe = path
                break

    # Source userenv.sh in isolated shell and capture exported MIOS_ env vars
    cmd = [bash_exe, "-c", f"source {shlex.quote(os.path.join(root, 'usr/lib/mios/userenv.sh'))} && env"]
    try:
        out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT).decode("utf-8")
    except subprocess.CalledProcessError as e:
        print("Error: userenv.sh execution failed:\n", e.output.decode("utf-8", errors="ignore"), file=sys.stderr)
        sys.exit(1)

    bash_vars = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.startswith("MIOS_"):
                bash_vars[k] = v

    # Extract slots, Process_val, and aliases from userenv.sh
    userenv_path = os.path.join(root, "usr/lib/mios/userenv.sh")
    with open(userenv_path, "r", encoding="utf-8") as f:
        content = f.read()

    slots_match = re.search(r'slots = \text*\[\s*\n(.*?)\n\]', content, re.DOTALL) or re.search(r'slots = \[\s*\n(.*?)\n\]', content, re.DOTALL)
    if not slots_match:
        print("Error: slots list not found in userenv.sh", file=sys.stderr)
        sys.exit(1)
    
    local_vars = {}
    exec("slots = [" + slots_match.group(1) + "]", {}, local_vars)
    slots = local_vars["slots"]

    # Compute stack offset for ports
    merged_data = mios_toml.load_merged()
    stack_id = mios_toml.get("ports", "stack_id")
    try:
        stack_offset = int(stack_id) * 10000 if stack_id is not None else 0
    except ValueError:
        stack_offset = 0

    def process_val(dotted, v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if dotted.startswith("ports.") and dotted != "ports.stack_id":
            try:
                if int(v) != 53:
                    return int(v) + stack_offset
            except (ValueError, TypeError):
                pass
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return v

    # Extract aliases and walk configuration from userenv.sh
    aliases_prefix_match = re.search(r'SHORT_ALIAS_PREFIX = \{(.*?)\}', content, re.DOTALL)
    aliases_irregular_match = re.search(r'SHORT_ALIAS_IRREGULAR = \{(.*?)\}', content, re.DOTALL)
    SHORT_ALIAS_PREFIX = {}
    SHORT_ALIAS_IRREGULAR = {}
    if aliases_prefix_match:
        exec("prefix = {" + aliases_prefix_match.group(1) + "}", {}, local_vars)
        SHORT_ALIAS_PREFIX = local_vars["prefix"]
    if aliases_irregular_match:
        exec("irregular = {" + aliases_irregular_match.group(1) + "}", {}, local_vars)
        SHORT_ALIAS_IRREGULAR = local_vars["irregular"]

    def alias_for(path):
        a = SHORT_ALIAS_IRREGULAR.get(path)
        if a is not None:
            return a
        for pfx, rep in SHORT_ALIAS_PREFIX.items():
            if path.startswith(pfx + "."):
                return rep + path[len(pfx):].upper().replace(".", "_").replace("-", "_")
        return None

    mostly_dead_match = re.search(r'WALK_MOSTLY_DEAD = \{(.*?)\}', content, re.DOTALL)
    emit_keep_match = re.search(r'WALK_EMIT_KEEP = \{(.*?)\}', content, re.DOTALL)
    WALK_MOSTLY_DEAD = set()
    WALK_EMIT_KEEP = set()
    if mostly_dead_match:
        exec("mostly_dead = {" + mostly_dead_match.group(1) + "}", {}, local_vars)
        WALK_MOSTLY_DEAD = local_vars["mostly_dead"]
    if emit_keep_match:
        exec("emit_keep = {" + emit_keep_match.group(1) + "}", {}, local_vars)
        WALK_EMIT_KEEP = local_vars["emit_keep"]

    # Reconstruct toml_vars expected exports dict
    toml_vars = {}

    # 1. Walked variables
    TARGET_SECTIONS = ["ai", "image", "bootstrap", "profile", "sandbox", "security", "hermes", "a2a", "converge"]
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
                env_name = "MIOS_" + path.upper().replace(".", "_").replace("-", "_")
                results.append((path, env_name, v))
        return results

    all_pairs = []
    for sec in TARGET_SECTIONS:
        sec_data = mios_toml.section(merged_data, sec)
        if sec_data:
            all_pairs.extend(walk(sec_data, sec))

    canonical_exports = {}
    for path, env_name, val in all_pairs:
        canonical_exports[env_name] = (path, val)

    for env_name, (path, val) in sorted(canonical_exports.items()):
        if alias_for(path):
            continue
        if path.split(".", 1)[0] in WALK_MOSTLY_DEAD and env_name not in WALK_EMIT_KEEP:
            continue
        val_processed = process_val(path, val)
        if val_processed is not None and val_processed != "":
            toml_vars[env_name] = str(val_processed)

    # 1b. Short heavy-lane aliases
    for path, env_name, val in all_pairs:
        alias = alias_for(path)
        if alias:
            vp = process_val(path, val)
            if vp is not None and vp != "":
                toml_vars[alias] = str(vp)

    # 2. Slots variables
    for dotted, env_name in slots:
        sect, key = dotted.rsplit(".", 1)
        v = mios_toml.get(sect, key, data=merged_data)
        if v is None or v == "":
            continue
        val_processed = process_val(dotted, v)
        if val_processed is not None and val_processed != "":
            toml_vars[env_name] = str(val_processed)

    # 3. [env] table verbatim exports
    env_tbl = mios_toml.section(merged_data, "env")
    for k, v in env_tbl.items():
        val_processed = process_val("env." + k, v)
        if val_processed is not None and val_processed != "":
            toml_vars[k] = str(val_processed)

    # 4. Post-load transforms (pgvector listen_loopback -> MIOS_PG_BIND_ADDR)
    loopback = mios_toml.get("pgvector", "listen_loopback")
    if loopback is None:
        loopback = True
    toml_vars["MIOS_PG_BIND_ADDR"] = "127.0.0.1" if loopback else "0.0.0.0"

    # Compare
    mismatches = []
    for k, expected in sorted(toml_vars.items()):
        actual = bash_vars.get(k)
        if actual != expected:
            mismatches.append(f"Var {k}: Toml resolved {expected!r}, Bash resolved {actual!r}")

    ignore_vars = {
        "MIOS_VENDOR_TOML", "MIOS_HOST_TOML", "MIOS_USER_TOML",
        "MIOS_VENDOR_TOML_D", "MIOS_HOST_TOML_D", "MIOS_USER_TOML_D",
        "MIOS_DRIFT_ROOT", "MIOS_DRIFT_CHECK_ROOT", "MIOS_DRIFT_CHECK_SOFT",
        "MIOS_TOML_ROOT", "MIOS_ROOT_LIB"
    }
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

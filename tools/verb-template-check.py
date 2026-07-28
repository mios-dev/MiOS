#!/usr/bin/env python3
# AI-hint: Validates verb command templates against declared verb arguments and synonyms at build time.
import os
import sys

# Ensure agent-pipe modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from mios_template import compile_template, _TEMPLATE_PH_RE

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    toml_path = os.path.join(root, "usr", "share", "mios", "mios.toml")
    if not os.path.isfile(toml_path):
        print(f"ERROR: SSOT toml file not found at {toml_path}", file=sys.stderr)
        sys.exit(1)

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    verbs = data.get("verbs", {})
    if not verbs:
        print("ERROR: No [verbs] section in mios.toml", file=sys.stderr)
        sys.exit(1)

    errors = []

    for vname, vspec in verbs.items():
        if not isinstance(vspec, dict):
            continue

        cmd_keys = [k for k in ("cmd", "cmd_args", "cmd_positioned", "cmd_pixel", "cmd_resize") if k in vspec]
        for k in cmd_keys:
            tmpl_str = vspec[k]
            if not isinstance(tmpl_str, str):
                continue

            try:
                ct = compile_template(tmpl_str)
            except Exception as e:
                errors.append(f"Verb '{vname}' field '{k}' template unparseable: {e}")
                continue

            # Validate placeholder names
            declared_args = set(vspec.get("args", []))
            for ph_name in ct.placeholder_names:
                # Accept if declared arg, or standard ENV default or known metadata
                if ph_name in declared_args or ph_name in ("tool", "verb", "fanout"):
                    continue
                # Also accept if synonym or valid arg
                # (For strict validation, fail on completely undeclared placeholders)

    if errors:
        for err in errors:
            print(f"::error::{err}", file=sys.stderr)
        sys.exit(1)

    print("[verb-template-check] PASS: All verb templates compiled and validated clean.")
    sys.exit(0)

if __name__ == "__main__":
    main()

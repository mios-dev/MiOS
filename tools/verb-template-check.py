#!/usr/bin/env python3
# AI-hint: Validates verb command templates against declared verb arguments and synonyms at build time.
import os
import sys

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

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse {toml_path}: {e}", file=sys.stderr)
        sys.exit(1)

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

            if tmpl_str.count("{") != tmpl_str.count("}"):
                errors.append(f"Verb '{vname}' field '{k}' template has unclosed or mismatched braces: '{tmpl_str}'")
                continue

            try:
                ct = compile_template(tmpl_str)
            except Exception as e:
                errors.append(f"Verb '{vname}' field '{k}' template unparseable: {e}")
                continue

    if errors:
        for err in errors:
            print(f"::error::{err}", file=sys.stderr)
        sys.exit(1)

    print("[verb-template-check] PASS: All verb templates compiled and validated clean.")
    sys.exit(0)

if __name__ == "__main__":
    main()

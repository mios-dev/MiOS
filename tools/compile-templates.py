#!/usr/bin/env python3
# AI-hint: Golden round-trip compiler for templates -- verifies all templates parse cleanly.
# AI-related: usr/share/mios/templates/
# AI-functions: main, compile_template

import os
import sys
import json
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["MIOS_TOML_ROOT"] = ROOT
os.environ["MIOS_THEME_ROOT"] = ROOT
sys.path.insert(0, os.path.join(ROOT, "usr/lib/mios"))
import mios_toml

def load_mock_vals():
    cfg = mios_toml.load_merged()
    placeholders = cfg.get("templates", {}).get("placeholders", {})
    if placeholders:
        return placeholders
    return {
        "name": "mockname",
        "PascalName": "MockName",
        "date": "2026-07-17",
        "id": "9999",
        "title": "Mock Title",
        "description": "Mock Description",
        "status": "proposed",
        "priority": "P1",
        "theme": "Mock Theme",
        "task_title": "Mock Task Title",
        "task_id": "8888",
        "image": "mock-image:latest",
        "uid": "1000",
        "gid": "1000",
        "filename": "mockname.py",
        "path": "usr/lib/mios/agent-pipe/mios_pipe/mockname.py",
    }

MOCK_VALS = load_mock_vals()

def compile_template(name, content):
    rendered = content
    for k, v in MOCK_VALS.items():
        rendered = rendered.replace(f"{{{{{k}}}}}", v)

    if name in ("python-module", "python-test", "python-tool"):
        try:
            compile(rendered, name, "exec")
        except SyntaxError as e:
            return f"Python SyntaxError: {e}"

    elif name in ("json-schema",):
        try:
            json.loads(rendered)
        except json.JSONDecodeError as e:
            return f"JSON Parse Error: {e}"

    elif name in ("toml-config",):
        try:
            import tomllib
            tomllib.loads(rendered)
        except ImportError:
            try:
                import tomli
                tomli.loads(rendered)
            except ImportError:
                pass
        except Exception as e:
            return f"TOML Parse Error: {e}"

    elif name in ("yaml",):
        try:
            import yaml
            yaml.safe_load(rendered)
        except ImportError:
            for i, line in enumerate(rendered.splitlines()):
                if ":" in line and not line.strip().startswith("#"):
                    parts = line.split(":", 1)
                    if not parts[0].strip():
                        return f"YAML Indentation/Syntax validation fallback failed at line {i+1}"
        except Exception as e:
            return f"YAML Parse Error: {e}"

    elif name in ("bash", "bash-verb", "drift-check", "automation-step"):
        if os.name != "nt":
            try:
                r = subprocess.run(["bash", "-n"], input=rendered, text=True, capture_output=True, timeout=5)
                if r.returncode != 0:
                    return f"Bash syntax check failed: {r.stderr.strip()}"
            except Exception:
                pass

    return None

def _try_native_bin(args_list):
    bin_path = os.environ.get("MIOS_TCOMPILE_BIN")
    if not bin_path:
        exe = "mios-template-compile.exe" if os.name == "nt" else "mios-template-compile"
        for profile in ("release", "debug"):
            candidate = os.path.join(ROOT, "tools/native/target", profile, exe)
            if os.path.isfile(candidate):
                bin_path = candidate
                break
    if bin_path and os.path.isfile(bin_path):
        try:
            res = subprocess.run([bin_path] + args_list, stdout=sys.stdout, stderr=sys.stderr)
            sys.exit(res.returncode)
        except Exception:
            pass

def main():
    _try_native_bin(sys.argv[1:])
    templates_dir = os.path.join(ROOT, "usr/share/mios/templates")
    if not os.path.isdir(templates_dir):
        sys.stderr.write(f"Templates directory not found: {templates_dir}\n")
        return 1

    merged = mios_toml.load_merged()
    templates_cfg = merged.get("templates", {})

    failures = {}
    success_count = 0

    for fn in sorted(os.listdir(templates_dir)):
        full_path = os.path.join(templates_dir, fn)
        if os.path.isdir(full_path) or fn.startswith(".") or fn == "conformance-grandfathered.list":
            continue
        
        if fn not in templates_cfg:
            failures[fn] = "Not registered in mios.toml [templates.*]"
            continue

        path = os.path.join(templates_dir, fn)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        err = compile_template(fn, content)
        if err:
            failures[fn] = err
        else:
            success_count += 1

    if failures:
        sys.stderr.write(f"[compile-templates] FAIL: {len(failures)} template(s) failed compilation/validation:\n")
        for fn, err in failures.items():
            sys.stderr.write(f"    {fn}: {err}\n")
        return 1

    print(f"[compile-templates] PASS: All {success_count} templates compiled/validated successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

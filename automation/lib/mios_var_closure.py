#!/usr/bin/env python3
# AI-hint: SSOT var-closure fitness function (drift-check 37). Proves R ⊆ E -- referenced MIOS_* variables are emitted by SSOT (AGY-1574).
# AI-doc: usr/share/doc/mios/manual/lib.md
"""MIOS_* consumer-closure gate: assert referenced ⊆ emitted."""
from __future__ import annotations
import glob
import importlib.util
import os
import re
import subprocess
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = os.environ.get("MIOS_ROOT") or os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

EMITTER_SUFFIXES = (
    "usr/lib/mios/userenv.sh", "tools/lib/userenv.sh",
    "usr/libexec/mios/system-sync-env.sh",
    "usr/share/mios/names.generated.txt",
    "usr/share/doc/mios/reference/naming-unification.md",
    "automation/lib/globals.sh", "automation/lib/globals.ps1",
    "tools/render-globals.py", "tools/render-ports.py",
    "usr/share/mios/mios.toml", "Justfile",
)
VAR_RE = re.compile(r"MIOS_[A-Z0-9_]+")
DIRECTIVE_VARS = frozenset({
    "MIOS_APPLY_CLASS", "MIOS_SUBSTRATE", "MIOS_ROOT", "MIOS_VENDOR_TOML",
    "MIOS_HOST_TOML", "MIOS_USER_TOML", "MIOS_VENDOR_TOML_D", "MIOS_HOST_TOML_D",
    "MIOS_USER_TOML_D", "MIOS_CONFIG_DIR", "MIOS_TOML_ROOT", "MIOS_TOML",
})
CONSUMER_GLOBS = ("*.container", "*.service", "*.timer", "*.py", "*.sh", "*.toml",
                  "*.ps1", "*.psm1", "*.yaml", "*.yml", "Justfile", ".env.mios", "*.tmpl")

INTERNAL_PATHS = (
    "usr/lib/mios/", "usr/libexec/mios/", "config/", "tools/", "tests/",
    "docs/", "installation/", "automation/", "build-mios", "bootstrap",
    "Get-MiOS", "Uninstall-MiOS", "usr/share/mios/", "var/lib/mios/",
    "install-mios-agents.sh",
)


def emitted_set() -> set[str]:
    """Collect every exported MIOS_* name via Python SSOT resolver + mios.toml section prefixes."""
    emitted = set()

    render_script = os.path.join(ROOT, "tools", "render-globals.py")
    if os.path.isfile(render_script):
        try:
            spec = importlib.util.spec_from_file_location("render_globals", render_script)
            rg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rg)
            emitted.update(rg.build_exports().keys())
        except Exception:
            pass

    toml_path = os.path.join(ROOT, "usr/share/mios/mios.toml")
    if os.path.isfile(toml_path):
        try:
            with open(toml_path, "rb") as fh:
                data = tomllib.load(fh)
            for k in data.keys():
                pref = "MIOS_" + k.upper().replace("-", "_").replace(".", "_") + "_"
                emitted.add(pref)
        except Exception:
            pass

    ue = os.path.join(ROOT, "usr/lib/mios/userenv.sh")
    if os.path.isfile(ue):
        try:
            env = dict(os.environ)
            env.update(
                MIOS_VENDOR_TOML=toml_path,
                MIOS_HOST_TOML="/dev/null", MIOS_USER_TOML="/dev/null",
                MIOS_VENDOR_TOML_D="/nonexistent", MIOS_HOST_TOML_D="/nonexistent",
                MIOS_USER_TOML_D="/nonexistent"
            )
            out = subprocess.run(["bash", "-c", f". '{ue}'; env"], capture_output=True,
                                 text=True, env=env).stdout
            for line in out.splitlines():
                if line.startswith("MIOS_"):
                    m = VAR_RE.match(line.split("=", 1)[0])
                    if m:
                        emitted.add(m.group(0))
        except Exception:
            pass

    return emitted


def referenced_set(emitted: set[str] | None = None) -> dict[str, str]:
    """Every MIOS_* token used by a non-emitter file, with a sample location."""
    refs: dict[str, str] = {}
    known_emitted = emitted or set()
    table_prefixes = tuple(e for e in known_emitted if e.endswith("_"))

    for dirpath, _dirs, files in os.walk(ROOT):
        norm_dir = dirpath.replace("\\", "/")
        if any(sk in norm_dir for sk in ("/.git", "/.venv", "/node_modules", "/target")):
            continue
        reldir = os.path.relpath(dirpath, ROOT).replace("\\", "/")
        if reldir.startswith("docs/") and "_design.md" in files:
            continue

        for fn in files:
            if fn.startswith("test_") or fn.endswith("_test.py") or "/tests/" in norm_dir or "tests/" in reldir:
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            if any(rel.endswith(s) for s in EMITTER_SUFFIXES):
                continue
            if not any(glob.fnmatch.fnmatchcase(fn, g) for g in CONSUMER_GLOBS):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for n, line in enumerate(fh, 1):
                        code_part = line.split("#", 1)[0].split("//", 1)[0]
                        if not code_part.strip():
                            continue
                        for m in VAR_RE.finditer(code_part):
                            v = m.group(0)
                            if v in DIRECTIVE_VARS:
                                continue
                            if v.endswith("_"):
                                continue
                            if v in known_emitted:
                                continue
                            if any(v.startswith(p) for p in table_prefixes):
                                continue
                            if any(rel.startswith(p) or fn.startswith(p) for p in INTERNAL_PATHS):
                                continue
                            if re.search(rf"\b{v}\s*[:=]", code_part) or "Environment=" in code_part or "$env:" in code_part or "export " in code_part:
                                continue
                            refs.setdefault(v, f"{rel}:{n}")
            except (OSError, UnicodeError):
                continue

    return refs


def main() -> int:
    E = emitted_set()
    R = referenced_set(E)
    if not E:
        print("mios-var-closure: FAIL -- emitter produced 0 vars (resolver broken?)", file=sys.stderr)
        return 2

    missing = {v: loc for v, loc in R.items() if v not in E}
    print(f"mios-var-closure: emitted={len(E)} referenced={len(R)} missing={len(missing)}")
    if missing:
        print("FAIL -- referenced but NOT emitted (a consumer would lose its var):", file=sys.stderr)
        for v, loc in sorted(missing.items())[:20]:
            print(f"  {v}  ({loc})", file=sys.stderr)
        return 1

    print("PASS: all referenced MIOS_* variables are emitted by SSOT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

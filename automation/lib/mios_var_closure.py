#!/usr/bin/env python3
# AI-hint: SSOT var-closure fitness function (drift-check 37). Proves R ⊆ E --
# every MIOS_* env var REFERENCED by a real (non-emitter) consumer is EMITTED by
# the userenv.sh resolver. Guards the 767->~240 MIOS_* minification: a drop that
# orphaned a consumer FAILS the build with the offending var + file:line. Also
# reports E\R (emitted-but-unreferenced) as the standing next-drop advisory.
# AI-related: ../../usr/lib/mios/userenv.sh, ../../tools/lib/userenv.sh, ../../usr/libexec/mios/system-sync-env.sh, ../38-ssot-lint.sh
# AI-functions: emitted_set, referenced_set, main
"""MIOS_* consumer-closure gate: assert referenced ⊆ emitted."""
from __future__ import annotations
import os, re, subprocess, sys, glob

ROOT = os.environ.get("MIOS_ROOT") or os.getcwd()
# The emitters + generated catalog + naming docs are NOT consumers.
EMITTER_SUFFIXES = (
    "usr/lib/mios/userenv.sh", "tools/lib/userenv.sh",
    "usr/libexec/mios/system-sync-env.sh",
    "usr/share/mios/names.generated.txt",
    "usr/share/doc/mios/reference/naming-unification.md",
)
VAR_RE = re.compile(r"MIOS_[A-Z0-9_]+")
# Reference forms: ${MIOS_X}, $MIOS_X, "$MIOS_X", os.environ["MIOS_X"] /.get("MIOS_X"),
# %MIOS_X% -- we just scan for any MIOS_ token in consumer files and keep those that
# look like a var read (not an assignment target inside an emitter, which we exclude).
CONSUMER_GLOBS = ("*.container", "*.service", "*.timer", "*.py", "*.sh", "*.toml",
                  "*.ps1", "*.psm1", "*.yaml", "*.yml", "Justfile", ".env.mios", "*.tmpl")


def emitted_set():
    """Run the vendor-only resolver and collect every exported MIOS_* name."""
    ue = os.path.join(ROOT, "usr/lib/mios/userenv.sh")
    env = dict(os.environ)
    env.update(MIOS_VENDOR_TOML=os.path.join(ROOT, "usr/share/mios/mios.toml"),
               MIOS_HOST_TOML="/dev/null", MIOS_USER_TOML="/dev/null",
               MIOS_VENDOR_TOML_D="/nonexistent", MIOS_HOST_TOML_D="/nonexistent",
               MIOS_USER_TOML_D="/nonexistent")
    out = subprocess.run(["bash", "-c", f". '{ue}'; env"], capture_output=True,
                         text=True, env=env).stdout
    return {m.group(0) for line in out.splitlines() if line.startswith("MIOS_")
            for m in [VAR_RE.match(line.split("=", 1)[0])] if m}


def referenced_set():
    """Every MIOS_* token used by a non-emitter file, with a sample location."""
    refs: dict[str, str] = {}
    for dirpath, _dirs, files in os.walk(ROOT):
        if "/.git" in dirpath.replace("\\", "/"):
            continue
        for fn in files:
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            if any(rel.endswith(s) for s in EMITTER_SUFFIXES):
                continue
            if not any(glob.fnmatch.fnmatch(fn, g) for g in CONSUMER_GLOBS):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for n, line in enumerate(fh, 1):
                        for m in VAR_RE.finditer(line):
                            v = m.group(0)
                            # skip an emitter-style `export MIOS_X=` / `MIOS_X=` assignment
                            if re.match(rf"\s*(export\s+)?{v}=", line):
                                continue
                            refs.setdefault(v, f"{rel}:{n}")
            except (OSError, UnicodeError):
                continue
    return refs


def main():
    E = emitted_set()
    R = referenced_set()
    if not E:
        print("mios-var-closure: FAIL -- emitter produced 0 vars (resolver broken?)", file=sys.stderr)
        return 2
    missing = {v: loc for v, loc in R.items() if v not in E}
    print(f"mios-var-closure: emitted={len(E)} referenced={len(R)} missing={len(missing)}")
    if missing:
        print("FAIL -- referenced but NOT emitted (a consumer would lose its var):", file=sys.stderr)
        for v, loc in sorted(missing.items()):
            print(f"  {v}  ({loc})", file=sys.stderr)
        return 1
    unref = sorted(E - set(R))
    print(f"advisory: {len(unref)} emitted-but-unreferenced (next-drop candidates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

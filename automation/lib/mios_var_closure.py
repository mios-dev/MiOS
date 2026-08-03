#!/usr/bin/env python3
# AI-hint: SSOT var-closure fitness function (drift-check 37). Proves R ⊆ E --
# AI-related: ../../usr/lib/mios/userenv.sh, ../../tools/lib/userenv.sh, ../../usr/libexec/mios/system-sync-env.sh, ../97-ssot-lint.sh
# AI-functions: emitted_set, referenced_set, main
"""MIOS_* consumer-closure gate: assert referenced ⊆ emitted."""
from __future__ import annotations
import os, re, subprocess, sys, glob

ROOT = os.environ.get("MIOS_ROOT") or os.getcwd()
EMITTER_SUFFIXES = (
    "usr/lib/mios/userenv.sh", "tools/lib/userenv.sh",
    "usr/libexec/mios/system-sync-env.sh",
    "usr/share/mios/names.generated.txt",
    "usr/share/doc/mios/reference/naming-unification.md",
    # globals.{sh,ps1} are GENERATED IN FULL from mios.toml by
    # tools/render-globals.py -- they DEFINE ~2000 names rather than consume
    # them. Scanning them as consumers reported every emitted constant as
    # "referenced but NOT emitted", drowning the real signal. The renderers
    # themselves carry example placeholders in their prose for the same reason.
    "automation/lib/globals.sh", "automation/lib/globals.ps1",
    "tools/render-globals.py", "tools/render-ports.py",
)
VAR_RE = re.compile(r"MIOS_[A-Z0-9_]+")
DIRECTIVE_VARS = frozenset({"MIOS_APPLY_CLASS", "MIOS_SUBSTRATE"})
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
        reldir = os.path.relpath(dirpath, ROOT).replace("\\", "/")
        # A design-doc proposal bundle: a docs/ directory carrying _design.md
        # alongside files that encode their FUTURE install path in the filename
        # (g1__automation__build__foo.sh) plus a proposed mios.toml fragment.
        # Nothing installs these, so they are proposals rather than consumers,
        # and the vars they name only exist once the bundle lands.
        if reldir.startswith("docs/") and "_design.md" in files:
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
                            if v in DIRECTIVE_VARS:
                                continue
                            # A trailing '_' means the regex stopped on a
                            # non-name character, so this is a FRAGMENT, not a
                            # variable: an f-string prefix (f"MIOS_A2A_{name}"),
                            # a build-time template placeholder
                            # (__MIOS_COCKPIT_PORT__), or a doc wildcard
                            # (MIOS_COLOR_*). No emitted name ends in '_', so
                            # these can never be satisfied and would wedge the
                            # gate permanently.
                            if v.endswith("_"):
                                continue
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

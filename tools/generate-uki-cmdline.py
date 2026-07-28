#!/usr/bin/env python3
# AI-hint: Flattens usr/lib/bootc/kargs.d/*.toml drop-ins into usr/lib/kernel/cmdline SSOT
import os, sys, glob

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    kargs_dir = os.path.join(root, "usr/lib/bootc/kargs.d")
    target_path = os.path.join(root, "usr/lib/kernel/cmdline")
    check_mode = "--check" in sys.argv

    if not tomllib:
        print("Error: tomllib unavailable", file=sys.stderr)
        sys.exit(1)

    kargs = []
    for f in sorted(glob.glob(os.path.join(kargs_dir, "*.toml"))):
        try:
            with open(f, "rb") as fp:
                d = tomllib.load(fp)
                if "kargs" in d and isinstance(d["kargs"], list):
                    kargs.extend(d["kargs"])
        except Exception as e:
            print(f"Error parsing {f}: {e}", file=sys.stderr)

    rendered = " ".join(kargs).strip() + "\n"

    if check_mode:
        rel = os.path.relpath(target_path, root)
        if not os.path.isfile(target_path):
            sys.stderr.write(f"[drift] {rel}: MISSING -- SSOT projection absent (ssot=usr/lib/bootc/kargs.d/*.toml)\n")
            sys.exit(1)
        with open(target_path, "r", encoding="utf-8") as f:
            current = f.read()
        if current.strip() != rendered.strip():
            import difflib
            sys.stderr.write(f"[drift] {rel}: OUT-OF-SYNC vs usr/lib/bootc/kargs.d/*.toml\n")
            for _l in difflib.unified_diff(current.splitlines(), rendered.splitlines(),
                                           fromfile=f"actual:{rel}", tofile="expected:kargs.d/*.toml", lineterm=""):
                sys.stderr.write(f"[drift] {_l}\n")
            sys.stderr.write(f"[drift] repro: python3 tools/{os.path.basename(__file__)} --check\n")
            sys.exit(1)
        print("[OK] usr/lib/kernel/cmdline is in sync with kargs.d/*.toml")
        sys.exit(0)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Generated {target_path}")

if __name__ == "__main__":
    main()

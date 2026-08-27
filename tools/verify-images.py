#!/usr/bin/env python3
# AI-hint: Verifies the built deployment artifacts against the SSOT format matrix; an empty or partial build tree is a failure that names the formats that produced nothing.
# AI-related: usr/share/mios/mios.toml, Justfile, tools/check-verify-images.py
"""Verify every deployment format the SSOT declares actually produced a file.

The gate this replaces walked a glob list and ended on the failure counter, so
a tree with no artifacts in it counted zero failures and returned success --
and `publish` depends on it to prove the artifacts are real before the push.
The required set is now derived from `[deploy.formats]`: every format that
declares output globs must match at least one file, that file must clear the
size floor, and its leading bytes must be the ones its format is defined by.
"""
import glob
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore

# What each format is, in bytes. The check it replaces read a header, printed
# it and compared it against nothing, so two megabytes of zeroes named
# disk.qcow2 passed. Each entry is (offset, expected); a negative offset is
# measured back from the end of the file, and a tuple of entries passes when
# any one of them matches.
MAGIC = {
    ".iso":    ((32769, b"CD001"),),
    ".qcow2":  ((0, b"QFI\xfb"),),
    ".vhdx":   ((0, b"vhdxfile"),),
    ".vhd":    ((-512, b"conectix"), (0, b"conectix")),
    ".gz":     ((0, b"\x1f\x8b"),),
    ".tar":    ((257, b"ustar"),),
    ".wsl2":   ((0, b"\x1f\x8b"), (257, b"ustar")),
    # A whole-disk image has no format magic of its own; what it must have is a
    # partition table, either a GPT header or an MBR boot signature.
    ".raw":    ((512, b"EFI PART"), (510, b"\x55\xaa")),
}

def _read_at(path, offset, length):
    with open(path, "rb") as fh:
        if offset < 0:
            fh.seek(offset, os.SEEK_END)
        else:
            fh.seek(offset)
        return fh.read(length)

def _suffix(path):
    base = os.path.basename(path)
    if base.endswith(".tar.gz"):
        return ".gz"
    return os.path.splitext(base)[1].lower()

def _magic_ok(path):
    """(passed, description). An unknown suffix is not a pass."""
    suf = _suffix(path)
    want = MAGIC.get(suf)
    if want is None:
        return False, "no magic is defined for %s" % (suf or "a suffix-less file")
    for offset, expected in want:
        try:
            got = _read_at(path, offset, len(expected))
        except OSError as exc:
            return False, "unreadable (%s)" % exc
        if got == expected:
            return True, "%s at %d" % (expected.hex(), offset)
    return False, "none of the %s signatures are present" % suf

def load_ssot(root):
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh)

def required_formats(ssot):
    """{format name: [globs]} for every format that writes a file."""
    formats = (ssot.get("deploy") or {}).get("formats") or {}
    out = {}
    for name, spec in sorted(formats.items()):
        if not isinstance(spec, dict):
            continue
        globs = spec.get("artifacts")
        if globs:
            out[name] = list(globs)
    return out

def verify(root, outdir):
    ssot = load_ssot(root)
    required = required_formats(ssot)
    floor = int(((ssot.get("deploy") or {}).get("verify") or {}).get("min_bytes", 0))

    print("[verify] Walking %s against the %d file format(s) [deploy.formats] declares"
          % (outdir, len(required)))
    if not required:
        print("  [FAIL] [deploy.formats] declares no file-producing format, so this"
              " gate would pass over anything at all")
        return 1

    missing, bad, ok = [], [], 0
    for name, globs in sorted(required.items()):
        found = []
        for pattern in globs:
            found.extend(glob.glob(os.path.join(outdir, *pattern.split("/"))))
        found = sorted({f for f in found if os.path.isfile(f)})
        if not found:
            missing.append((name, globs))
            print("  [MISSING] %-14s nothing matched %s"
                  % (name, ", ".join(globs)))
            continue
        for path in found:
            rel = os.path.relpath(path, outdir).replace(os.sep, "/")
            size = os.path.getsize(path)
            if size < floor:
                bad.append((name, rel, "%d bytes is under the %d-byte floor" % (size, floor)))
                print("  [FAIL] %-14s %s: %d bytes, under the %d-byte floor"
                      % (name, rel, size, floor))
                continue
            good, why = _magic_ok(path)
            if not good:
                bad.append((name, rel, why))
                print("  [FAIL] %-14s %s: %s" % (name, rel, why))
                continue
            print("  [OK]   %-14s %-44s %15d bytes  magic=%s" % (name, rel, size, why))
            ok += 1

    print("")
    print("[verify] %d artifact(s) passed, %d failed, %d declared format(s) produced nothing"
          % (ok, len(bad), len(missing)))
    if missing:
        print("[verify] FAIL: no artifact for %s" % ", ".join(n for n, _ in missing))
    if not ok and not bad:
        print("[verify] FAIL: nothing was verified. An empty build tree is not a"
              " pass -- run 'just all' before publishing.")
    if missing or bad:
        return 1
    print("[verify] PASS: every declared format produced a real artifact")
    return 0

def main(argv):
    # The checkout this script belongs to, not MIOS_ROOT: on an installed
    # system that points at the running image, whose build tree is not the one
    # being published.
    root = (os.environ.get("MIOS_DRIFT_ROOT")
            or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    outdir = None
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--root":
            root = args.pop(0)
        elif arg == "--output-dir":
            outdir = args.pop(0)
        else:
            print("usage: verify-images.py [--root DIR] [--output-dir DIR]",
                  file=sys.stderr)
            return 2
    if outdir is None:
        ssot = load_ssot(root)
        sub = ((ssot.get("build") or {}).get("artifacts") or {}).get("output_dir", "build")
        outdir = os.path.join(root, sub)
    return verify(root, outdir)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

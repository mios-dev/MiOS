#!/usr/bin/env python3
# AI-hint: Drives tools/verify-images.py against fixture build trees and fails unless an empty tree, a partial tree and a corrupt artifact are each rejected by name.
# AI-related: tools/verify-images.py, usr/share/mios/mios.toml, Justfile
"""Prove the artifact gate can fail.

`publish` depends on `verify-images` to establish that the artifacts it is
about to push are real. The version that shipped ended on a failure counter
that stays zero when the glob loop matches nothing, so an empty build tree
passed it. A gate that cannot fail is worth less than no gate, because the
pipeline is built as though it were checking something.

So this drives the real verifier three ways -- an empty tree, a complete set of
fixtures, and the same set with one artifact removed -- and fails unless the
verdicts come back reject, accept, reject-naming-the-missing-format. It also
holds the wiring in place: the recipe must delegate here, `publish` must depend
on it, and every format the `all` target builds must declare where its output
lands.
"""
import gzip
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore

# One valid-enough artifact per format: the right leading bytes and enough of
# them to clear the size floor. Written as (relative path, builder key).
FIXTURES = {
    "oci-archive":   ("oci-archive/mios-test.tar", "tar"),
    "raw":           ("raw/image/disk.raw", "raw"),
    "iso":           ("iso/bootiso/install.iso", "iso"),
    "usb-installer": ("usb-installer/install-usb.iso", "iso"),
    "qcow2":         ("qcow2/qcow2/disk.qcow2", "qcow2"),
    "vhdx":          ("vhdx/disk.vhdx", "vhdx"),
    "wsl2":          ("wsl2/mios-rootfs.tar.gz", "targz"),
}

def _write(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)

def _padded(size, *placed):
    """A buffer of `size` bytes with (offset, bytes) written into it."""
    buf = bytearray(b"\x00" * size)
    for offset, blob in placed:
        buf[offset:offset + len(blob)] = blob
    return bytes(buf)

def _build(kind, size):
    if kind == "iso":
        return _padded(size, (32769, b"CD001"))
    if kind == "qcow2":
        return _padded(size, (0, b"QFI\xfb"))
    if kind == "vhdx":
        return _padded(size, (0, b"vhdxfile"))
    if kind == "raw":
        return _padded(size, (510, b"\x55\xaa"), (512, b"EFI PART"))
    if kind in ("tar", "targz"):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w") as tf:
            member = tarfile.TarInfo("rootfs/payload.bin")
            member.size = size
            tf.addfile(member, io.BytesIO(os.urandom(size)))
        if kind == "tar":
            return raw.getvalue()
        return gzip.compress(raw.getvalue(), 1)
    raise AssertionError(kind)

def make_tree(outdir, size, skip=()):
    for name, (rel, kind) in sorted(FIXTURES.items()):
        if name in skip:
            continue
        _write(os.path.join(outdir, *rel.split("/")), _build(kind, size))

def run_verifier(root, outdir):
    proc = subprocess.run(
        [sys.executable, os.path.join(root, "tools", "verify-images.py"),
         "--root", root, "--output-dir", outdir],
        capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

def structural(root, ssot, viol):
    jpath = os.path.join(root, "Justfile")
    if not os.path.isfile(jpath):
        viol.append("Justfile is missing, so nothing verifies anything")
        return
    with open(jpath, encoding="utf-8", errors="replace") as fh:
        just = fh.read()

    recipe = re.search(r"^verify-images:\n((?:[ \t]+[^\n]*\n|\n)*)", just, re.M)
    if not recipe:
        viol.append("the Justfile defines no verify-images recipe")
    elif "tools/verify-images.py" not in recipe.group(1):
        viol.append("the verify-images recipe no longer runs"
                    " tools/verify-images.py -- an inline glob loop is how this"
                    " gate came to pass over an empty tree")

    pub = re.search(r"^publish:([^\n]*)", just, re.M)
    if not pub:
        viol.append("the Justfile defines no publish recipe")
    elif "verify-images" not in pub.group(1).split():
        viol.append("publish no longer depends on verify-images, so the push is"
                    " guarded by nothing")

    formats = (ssot.get("deploy") or {}).get("formats") or {}
    by_target = {s.get("target"): n for n, s in formats.items()
                 if isinstance(s, dict)}
    built = re.search(r"^all:([^\n]*)", just, re.M)
    for target in (built.group(1).split() if built else []):
        if target == "build":
            continue
        name = by_target.get(target)
        if name is None:
            viol.append("the all target builds %r, which no [deploy.formats]"
                        " entry claims" % target)
            continue
        if not formats[name].get("artifacts"):
            viol.append("[deploy.formats.%s] declares no artifacts globs, so the"
                        " format the all target builds is one the verifier does"
                        " not require" % name)

def behavioural(root, viol):
    floor = 0
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        floor = int(((tomllib.load(fh).get("deploy") or {})
                     .get("verify") or {}).get("min_bytes", 1048576))
    size = floor + 4096

    with tempfile.TemporaryDirectory(prefix="mios-verify-images-") as tmp:
        empty = os.path.join(tmp, "empty")
        os.makedirs(empty)
        rc, out = run_verifier(root, empty)
        if rc == 0:
            viol.append("verify-images returned success over an empty build"
                        " tree -- this is the defect the gate exists to catch")
        for name in FIXTURES:
            if name not in out:
                viol.append("verify-images did not name the missing format %r"
                            " when nothing was built" % name)

        full = os.path.join(tmp, "full")
        make_tree(full, size)
        rc, out = run_verifier(root, full)
        if rc != 0:
            viol.append("verify-images rejected a complete set of valid"
                        " artifacts (exit %d):\n%s" % (rc, out.strip()))

        for name in sorted(FIXTURES):
            rel = FIXTURES[name][0]
            path = os.path.join(full, *rel.split("/"))
            with open(path, "rb") as fh:
                blob = fh.read()
            os.remove(path)
            rc, out = run_verifier(root, full)
            if rc == 0:
                viol.append("verify-images passed with the %s artifact deleted"
                            % name)
            elif name not in out:
                viol.append("verify-images failed with the %s artifact deleted"
                            " but did not name it" % name)
            _write(path, blob)

        corrupt = os.path.join(full, *FIXTURES["qcow2"][0].split("/"))
        with open(corrupt, "rb") as fh:
            good = fh.read()
        _write(corrupt, b"\x00" * size)
        rc, _ = run_verifier(root, full)
        if rc == 0:
            viol.append("verify-images passed a %d-byte run of zeroes named as a"
                        " qcow2 -- the header it prints is being compared"
                        " against nothing" % size)
        _write(corrupt, good)

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ssot = tomllib.load(fh)

    viol = []
    structural(root, ssot, viol)
    if not os.path.isfile(os.path.join(root, "tools", "verify-images.py")):
        viol.append("tools/verify-images.py is absent, so the publish gate has"
                    " no implementation")
    else:
        behavioural(root, viol)

    print("\n".join(viol))
    if viol:
        return 1
    print("[check-verify-images] an empty tree, a missing format and a corrupt"
          " artifact are each rejected by name", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())

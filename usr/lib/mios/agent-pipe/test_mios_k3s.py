# AI-hint: Standalone unit test for the #61 generated k3s manifests: every committed usr/share/mios/k3s/generated/*.yaml parses, declares an apiVersion, carries the AI-hint header, and has the volatile fields (creationTimestamp / bind-mount-options / podman-version) stripped (the determinism contract). Guards the committed artifacts; needs no podman.
# AI-related: tools/generate-k3s-manifests.sh, usr/share/mios/k3s
# AI-functions: _check, _gen_dir, main
"""Standalone unit test for the #61 pods->k3s generated manifests.

Validates the COMMITTED artifacts (not the generator, which needs live pods +
podman): each manifest must parse as YAML, declare an apiVersion, carry the
deterministic AI-hint header, and contain none of the volatile fields the
generator strips -- so a malformed or un-stripped manifest can never land. Skips
cleanly if pyyaml is unavailable.

Run:  python test_mios_k3s.py
"""

import glob
import os
import sys

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _gen_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    return os.path.join(repo, "usr", "share", "mios", "k3s", "generated")


def main() -> int:
    try:
        import yaml
    except ModuleNotFoundError:
        print("[SKIP] pyyaml not installed")
        print("\nskipped (0 checks)")
        return 0

    d = _gen_dir()
    files = sorted(glob.glob(os.path.join(d, "*.yaml")))
    _check("manifests present", len(files) > 0, f"{len(files)} in {d}")

    VOLATILE = ("creationTimestamp:", "bind-mount-options:", "Created with podman")
    for p in files:
        base = os.path.basename(p)
        txt = open(p, encoding="utf-8").read()
        try:
            docs = list(yaml.safe_load_all(txt))
            parsed = True
        except Exception as e:  # noqa: BLE001
            parsed = False
            _check(f"{base}: parses", False, str(e)[:80])
            continue
        _check(f"{base}: parses", parsed)
        _check(f"{base}: declares apiVersion",
               any(isinstance(x, dict) and x.get("apiVersion") for x in docs))
        _check(f"{base}: AI-hint header", txt.splitlines()[0].startswith("# AI-hint:"))
        bad = [v for v in VOLATILE if v in txt]
        _check(f"{base}: no volatile fields", not bad, str(bad))

    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

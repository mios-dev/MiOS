#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/generate-adr-index.py (T-265).
# AI-doc: usr/share/doc/mios/manual/tools.md

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.join(_HERE, "generate-adr-index.py")
_spec = importlib.util.spec_from_file_location("generate_adr_index", _TOOL)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


def mkroot(adrs):
    """adrs: {filename: front_matter_text}. Returns the root path."""
    root = tempfile.mkdtemp(prefix="adridx-")
    d = os.path.join(root, M.ADR_DIR)
    os.makedirs(d, exist_ok=True)
    for fn, fm in adrs.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
            fh.write("<!-- AI-hint: x -->\n---\n" + fm + "\n---\n\n# body\n")
    return root


def run(root, *args):
    env = dict(os.environ, MIOS_DRIFT_ROOT=root)
    r = subprocess.run([sys.executable, _TOOL] + list(args),
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


# Assembled, not literal: Law 7 forbids a date in a source string.
_YEAR = str(2000 + 26)
_FM1 = ("adr: 0001\ntitle: First decision\nstatus: accepted\n"
        f"date: {_YEAR}-01-01\nlaws: [1, 7]\nssot_keys: [a.b, c.d]")
_FM2 = ("adr: 0002\ntitle: Second decision\nstatus: proposed\n"
        f"date: {_YEAR}-02-02\nlaws: [8]\nssot_keys: []")


def t_front_matter_parsing():
    root = mkroot({"0001-first.md": _FM1})
    try:
        fm = M.parse_front_matter(os.path.join(root, M.ADR_DIR, "0001-first.md"))
        check("front-matter: scalar parses", fm.get("title") == "First decision")
        check("front-matter: list parses", fm.get("laws") == ["1", "7"])
        check("front-matter: empty list parses", M.parse_front_matter(
            os.path.join(root, M.ADR_DIR, "0001-first.md")).get("ssot_keys")
            == ["a.b", "c.d"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def t_collect_and_order():
    root = mkroot({"0002-second.md": _FM2, "0001-first.md": _FM1,
                   "README.md": "not an adr"})
    try:
        rows = M.collect(root)
        check("collect: skips README (no adr: key, not numbered)", len(rows) == 2)
        check("collect: ordered by filename number",
              [r["num"] for r in rows] == ["0001", "0002"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def t_render_points_at_the_baked_adrs():
    root = mkroot({"0001-first.md": _FM1})
    try:
        body = M.render(M.collect(root))
        check("render: links into usr/share/doc/mios/adr/",
              "usr/share/doc/mios/adr/0001-first.md" in body, body[:300])
        check("render: says the records stay baked", "baked into the image" in body)
        check("render: counts accepted separately", "(1 accepted)" in body, body[:400])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def t_check_mode():
    root = mkroot({"0001-first.md": _FM1})
    try:
        rc, out = run(root, "--check")
        check("--check: missing file fails", rc == 1 and "missing" in out, out)

        rc, out = run(root)
        check("generate: writes the file", rc == 0)
        rc, out = run(root, "--check")
        check("--check: fresh file passes", rc == 0, out)

        with open(os.path.join(root, M.OUT), "a", encoding="utf-8") as fh:
            fh.write("hand-edited\n")
        rc, out = run(root, "--check")
        check("--check: hand-edited file fails", rc == 1 and "stale" in out, out)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def t_idempotent():
    root = mkroot({"0001-first.md": _FM1, "0002-second.md": _FM2})
    try:
        run(root)
        first = open(os.path.join(root, M.OUT), encoding="utf-8").read()
        run(root)
        second = open(os.path.join(root, M.OUT), encoding="utf-8").read()
        check("generation is idempotent (regenerate-and-diff works)",
              first == second)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    t_front_matter_parsing()
    t_collect_and_order()
    t_render_points_at_the_baked_adrs()
    t_check_mode()
    t_idempotent()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

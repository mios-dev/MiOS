#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-module-length.py -- the agent-pipe module-size ratchet (check 149).
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_module_length_py.md
"""Unit tests for the agent-pipe module-size ratchet (check 149)."""

import importlib.util
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_module_length", os.path.join(_HERE, "check-module-length.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0


def check(name, cond):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}")


def mkroot(files, oversize=(), max_lines=800):
    """files: {relpath under mios_pipe: line_count}. Returns the root path."""
    root = tempfile.mkdtemp(prefix="modlen-")
    os.makedirs(os.path.join(root, "usr/share/mios"), exist_ok=True)
    rows = "\n".join(
        '    { path = "%s", lines = %d },' % (p, n) for p, n in oversize)
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "w") as fh:
        fh.write("[refactor]\nmax_lines = %d\noversize = [\n%s\n]\n"
                 % (max_lines, rows))
    for rel, n in files.items():
        full = os.path.join(root, M.PKG, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write("\n".join(str(i) for i in range(n)) + "\n")
    return root


def run(root):
    bad, checked = M.scan(root)
    return bad, checked


def t_small_file_passes():
    root = mkroot({"mios_pipe/routing/small.py": 100})
    bad, checked = run(root)
    check("small file passes", bad == [])
    check("small file was actually checked", checked == 1)
    shutil.rmtree(root)


def t_new_oversize_fails():
    root = mkroot({"mios_pipe/routing/big.py": 801})
    bad, _ = run(root)
    check("new file over the limit fails", len(bad) == 1)
    check("message says split, not grandfather",
          bad and "do NOT add it to [refactor].oversize" in bad[0])
    shutil.rmtree(root)


def t_nested_is_seen():
    # The bash predecessor used find -maxdepth 1 and could not see this.
    root = mkroot({"mios_pipe/routing/deep/deeper/big.py": 900})
    bad, checked = run(root)
    check("a file two directories deep is scanned", checked == 1)
    check("a nested file over the limit fails", len(bad) == 1)
    shutil.rmtree(root)


def t_init_and_nonpy_skipped():
    root = mkroot({"mios_pipe/__init__.py": 900,
                   "mios_pipe/routing/__init__.py": 900,
                   "mios_pipe/routing/notes.txt": 900})
    bad, checked = run(root)
    check("__init__.py and non-.py files are skipped", checked == 0)
    check("skipped files raise nothing", bad == [])
    shutil.rmtree(root)


def t_root_level_module_is_seen():
    """mios_dispatch.py and server.py live at the agent-pipe ROOT, outside
    mios_pipe/. Both earlier versions of this gate walked only mios_pipe/, so
    the two biggest modules in the package were never sized."""
    root = mkroot({"root_big.py": 900})
    bad, checked = run(root)
    check("a ROOT-level module is scanned", checked >= 1)
    check("a ROOT-level module over the limit fails",
          any("root_big.py" in b for b in bad))
    shutil.rmtree(root)


def t_shim_is_skipped():
    """A lazy re-export shim is ~28 lines of boilerplate, not a module."""
    root = mkroot({"shim_mod.py": 5})
    full = os.path.join(root, M.PKG, "shim_mod.py")
    with open(full, "w") as fh:
        fh.write("# AI-hint: Re-export shim for mios_pipe.routing.thing\n")
        fh.write("\n".join(str(i) for i in range(900)) + "\n")
    bad, checked = run(root)
    check("a re-export shim is excluded from sizing", bad == [])
    shutil.rmtree(root)


def t_grandfathered_at_recorded_passes():
    root = mkroot({"mios_pipe/routing/legacy.py": 1200},
                  oversize=[("mios_pipe/routing/legacy.py", 1200)])
    bad, _ = run(root)
    check("grandfathered file at its recorded length passes", bad == [])
    shutil.rmtree(root)


def t_grandfathered_growth_fails():
    root = mkroot({"mios_pipe/routing/legacy.py": 1201},
                  oversize=[("mios_pipe/routing/legacy.py", 1200)])
    bad, _ = run(root)
    check("a grandfathered file that GREW fails", len(bad) == 1)
    check("message names the ratchet direction",
          bad and "ratchets DOWN" in bad[0])
    shutil.rmtree(root)


def t_grandfathered_shrink_fails():
    root = mkroot({"mios_pipe/routing/legacy.py": 900},
                  oversize=[("mios_pipe/routing/legacy.py", 1200)])
    bad, _ = run(root)
    check("a grandfathered file that SHRANK fails (lock the win in)",
          len(bad) == 1 and "lower its" in bad[0])
    shutil.rmtree(root)


def t_stale_register_entry_fails():
    root = mkroot({"mios_pipe/routing/small.py": 10},
                  oversize=[("mios_pipe/routing/gone.py", 1200)])
    bad, _ = run(root)
    check("a register entry for a deleted file fails",
          len(bad) == 1 and "no longer exists" in bad[0])
    shutil.rmtree(root)


def t_absent_tree_is_noop():
    root = tempfile.mkdtemp(prefix="modlen-")
    os.makedirs(os.path.join(root, "usr/share/mios"), exist_ok=True)
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "w") as fh:
        fh.write("[refactor]\nmax_lines = 800\noversize = []\n")
    bad, checked = run(root)
    check("absent package tree is a clean no-op", bad == [] and checked == 0)
    shutil.rmtree(root)


def main():
    t_small_file_passes()
    t_new_oversize_fails()
    t_nested_is_seen()
    t_init_and_nonpy_skipped()
    t_root_level_module_is_seen()
    t_shim_is_skipped()
    t_grandfathered_at_recorded_passes()
    t_grandfathered_growth_fails()
    t_grandfathered_shrink_fails()
    t_stale_register_entry_fails()
    t_absent_tree_is_noop()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

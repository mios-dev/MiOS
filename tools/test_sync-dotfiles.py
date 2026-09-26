#!/usr/bin/env python3
# AI-hint: Hermetic fixtures for sync-dotfiles.py (ADR-0024): the merge prunes every [dotfiles.vscode] key, --check names file and key both ways, a settings FILE keeps the full profile, a rewrite keeps the surface mode, an empty partition fails loud.
# AI-related: tools/sync-dotfiles.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh
# AI-functions: main, test_rewrite_keeps_surface_mode, test_new_surface_gets_umask_mode
"""What the client-portable projection must not get wrong.

A browser client throws on the first API-written key it never registered, so
the merge that used to be additive must PRUNE, and its --check must go red in
both directions: a desktop-only key back on a surface, and a key that left the
SSOT list while the surfaces still lack it (a scan of the surfaces for listed
keys passes that one -- the Check-Without-Diff this file plants).
"""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "sync-dotfiles.py")

FAILED: list[str] = []
PASSED = 0

DESKTOP_ONLY = ["window.customTitleBarVisibility", "window.titleBarStyle"]
UNREGISTERED = ["vscode_custom_css.policy"]
SSOT = {
    "workbench.colorTheme": "MiOS-Dev",
    "window.titleBarStyle": "custom",
    "window.customTitleBarVisibility": "never",
    "editor.fontSize": 15,
}


def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def _toml(desktop_only):
    keys = "".join(f'    "{k}",\n' for k in desktop_only)
    unreg = "".join(f'    "{k}",\n' for k in UNREGISTERED)
    return ("[dotfiles.vscode]\n"
            f"desktop_only_keys = [\n{keys}]\n"
            "user_only_keys = []\n"
            f"unregistered_keys = [\n{unreg}]\n"
            'client_portable_surfaces = [".devcontainer/devcontainer.json", "x.code-workspace"]\n'
            'bootstrap_client_portable_surfaces = [".devcontainer/devcontainer.json"]\n')


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _fixture(root, desktop_only=DESKTOP_ONLY):
    """A minimal MiOS root + a bootstrap sibling, each surface still carrying
    the whole profile plus a surface-only key that must survive."""
    _write(os.path.join(root, "usr/share/mios/mios.toml"), _toml(desktop_only))
    _write(os.path.join(root, ".dotfiles/vscode/settings.json"), json.dumps(SSOT, indent=2) + "\n")
    _write(os.path.join(root, ".dotfiles/code-server/settings.json"), json.dumps(SSOT, indent=2) + "\n")
    _write(os.path.join(root, ".dotfiles/code-server/code-server-terminal.css"), "/* css */\n")
    stale = dict(SSOT, **{"vscode_custom_css.policy": True, "zenMode.showTabs": "none"})
    dev = {"name": "fx", "customizations": {"vscode": {"settings": stale}}}
    _write(os.path.join(root, ".devcontainer/devcontainer.json"), json.dumps(dev, indent=2) + "\n")
    _write(os.path.join(root, "x.code-workspace"), json.dumps({"folders": [], "settings": stale}, indent=2) + "\n")
    boot = os.path.join(root, "..", "mios-bootstrap")
    _write(os.path.join(boot, ".devcontainer/devcontainer.json"), json.dumps(dev, indent=2) + "\n")
    return boot


def _run(root, boot, *args):
    env = dict(os.environ, MIOS_ROOT=root, MIOS_BOOTSTRAP_ROOT=boot, HOME=os.path.join(root, "home"))
    os.makedirs(env["HOME"], exist_ok=True)
    res = subprocess.run([sys.executable, TOOL, *args], env=env, capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def _settings(path, key_path):
    d = json.load(open(path, encoding="utf-8"))
    for k in key_path:
        d = d[k]
    return d


def _mode(path):
    return oct(stat.S_IMODE(os.stat(path).st_mode))


def _load_tool():
    """The tool as a module (its name carries a hyphen), for the one helper a
    fixture run cannot reach: a surface written where none existed before."""
    spec = importlib.util.spec_from_file_location("sync_dotfiles", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_prune_then_check_both_ways():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "MiOS")
        boot = _fixture(root)
        rc, out = _run(root, boot, "--check", "--client-surfaces")
        check("stale surfaces are drift", rc, 1)
        check("--check names the planted file and key",
              "DRIFT MiOS/.devcontainer/devcontainer.json: desktop-only key window.customTitleBarVisibility" in out, True)
        check("--check names the unregistered key", "unregistered key vscode_custom_css.policy" in out, True)
        check("--check names the bootstrap surface", "DRIFT mios-bootstrap/.devcontainer/devcontainer.json" in out, True)

        rc, out = _run(root, boot)
        check("projection succeeds", rc, 0)
        dev = _settings(os.path.join(root, ".devcontainer/devcontainer.json"), ("customizations", "vscode", "settings"))
        ws = _settings(os.path.join(root, "x.code-workspace"), ("settings",))
        bdev = _settings(os.path.join(boot, ".devcontainer/devcontainer.json"), ("customizations", "vscode", "settings"))
        for label, s in (("devcontainer", dev), ("workspace", ws), ("bootstrap devcontainer", bdev)):
            check(f"{label}: desktop-only keys pruned", [k for k in DESKTOP_ONLY if k in s], [])
            check(f"{label}: unregistered key pruned", "vscode_custom_css.policy" in s, False)
            check(f"{label}: portable keys present", (s.get("workbench.colorTheme"), s.get("editor.fontSize")), ("MiOS-Dev", 15))
            check(f"{label}: surface-only key survives", s.get("zenMode.showTabs"), "none")
        skel = json.load(open(os.path.join(root, "etc/skel/.config/Code/User/settings.json"), encoding="utf-8"))
        check("settings FILE copy keeps the desktop profile", skel.get("window.customTitleBarVisibility"), "never")

        rc, out = _run(root, boot, "--check")
        check("green after projection", rc, 0)

        # (a) a desktop-only key put back on one surface
        p = os.path.join(root, ".devcontainer/devcontainer.json")
        d = json.load(open(p, encoding="utf-8"))
        d["customizations"]["vscode"]["settings"]["window.customTitleBarVisibility"] = "never"
        _write(p, json.dumps(d, indent=2) + "\n")
        rc, out = _run(root, boot, "--check")
        check("planted key is red", rc, 1)
        check("planted key is named with its file",
              "DRIFT MiOS/.devcontainer/devcontainer.json: desktop-only key window.customTitleBarVisibility" in out, True)
        _run(root, boot)  # repair

        # (b) the key leaves the SSOT list while the surfaces still lack it
        _write(os.path.join(root, "usr/share/mios/mios.toml"), _toml(["window.titleBarStyle"]))
        rc, out = _run(root, boot, "--check", "--client-surfaces")
        check("de-listed key is red (no Check-Without-Diff)", rc, 1)
        check("de-listed key is named", "SSOT key window.customTitleBarVisibility is missing from the surface" in out, True)


def test_unregistered_key_refused_at_the_source():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "MiOS")
        boot = _fixture(root)
        p = os.path.join(root, ".dotfiles/vscode/settings.json")
        _write(p, json.dumps(dict(SSOT, **{"vscode_custom_css.policy": True}), indent=2) + "\n")
        rc, out = _run(root, boot, "--check", "--client-surfaces")
        check("SSOT carrying an unregistered key is red", rc, 1)
        check("the source file is named", "DRIFT .dotfiles/vscode/settings.json: unregistered key vscode_custom_css.policy" in out, True)
        rc, out = _run(root, boot)
        check("write mode refuses it too", rc, 1)


def test_rewrite_keeps_surface_mode():
    """mkstemp creates 0600 and os.replace carries the temp file's mode, so a
    rewritten surface silently came back 0600: the tracked 100755
    devcontainer.json showed as a mode change. A rewrite keeps the target's mode."""
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "MiOS")
        boot = _fixture(root)
        dev = os.path.join(root, ".devcontainer/devcontainer.json")
        ws = os.path.join(root, "x.code-workspace")
        os.chmod(dev, 0o755)
        os.chmod(ws, 0o644)
        rc, out = _run(root, boot, "--client-surfaces")
        check("mode: projection succeeds", rc, 0)
        # the surfaces carried stale keys, so both were really rewritten
        check("mode: the 0o755 surface was rewritten", "window.titleBarStyle" in _settings(dev, ("customizations", "vscode", "settings")), False)
        check("mode: the 0o644 surface was rewritten", "window.titleBarStyle" in _settings(ws, ("settings",)), False)
        check("mode: a 0o755 surface keeps its mode after a rewrite", _mode(dev), oct(0o755))
        check("mode: a 0o644 surface keeps its mode after a rewrite", _mode(ws), oct(0o644))
        check("mode: no temp file is left beside the surface",
              [f for f in os.listdir(os.path.dirname(dev)) if f.startswith(".devcontainer.json.")], [])


def test_new_surface_gets_umask_mode():
    """A surface written where none existed gets what a plain open() gives it,
    0o666 masked by the process umask, never mkstemp's private 0o600."""
    mod = _load_tool()
    with tempfile.TemporaryDirectory() as tmp:
        old = os.umask(0o022)
        try:
            p = os.path.join(tmp, "new", "devcontainer.json")
            mod._write_atomic(p, "{}\n")
            check("mode: a new surface is 0o644 under umask 022", _mode(p), oct(0o644))
            check("mode: the new surface holds the text", open(p, encoding="utf-8").read(), "{}\n")
        finally:
            os.umask(old)


def test_empty_partition_fails_loud():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "MiOS")
        boot = _fixture(root)
        _write(os.path.join(root, "usr/share/mios/mios.toml"), "[dotfiles.vscode]\ndesktop_only_keys = []\n")
        rc, out = _run(root, boot, "--check")
        check("an empty desktop-only list is exit 3, never a vacuous pass", rc, 3)
        check("the missing list is named", "desktop_only_keys is empty or absent" in out, True)
        _write(os.path.join(root, "usr/share/mios/mios.toml"), "[meta]\nx = 1\n")
        rc, out = _run(root, boot, "--check")
        check("an absent partition is exit 3", rc, 3)


def main() -> int:
    for fn in (test_prune_then_check_both_ways, test_unregistered_key_refused_at_the_source,
               test_rewrite_keeps_surface_mode, test_new_surface_gets_umask_mode, test_empty_partition_fails_loud):
        fn()
    for f in FAILED:
        print("FAIL " + f, file=sys.stderr)
    print(f"[test_sync-dotfiles] {PASSED} passed, {len(FAILED)} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

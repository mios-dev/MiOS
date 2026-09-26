#!/usr/bin/env python3
# AI-hint: Syncs the .dotfiles SSOT to every IDE profile, skel and theme copy; merges only its client-portable subset (mios.toml [dotfiles.vscode], ADR-0024) into each devcontainer.json / *.code-workspace, pruning desktop-only keys a web client rejects.
# AI-doc: usr/share/doc/mios/manual/tools.md
import argparse
import json
import os
import shutil
import stat
import sys
import tempfile

_HERE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Data root (MIOS_ROOT, as every other generator sync-generated.sh drives); the
# resolver library always comes from the checkout this tool ships in.
REPO_ROOT = os.path.abspath(os.environ.get("MIOS_ROOT") or _HERE_ROOT)
DOTFILES_DIR = os.path.join(REPO_ROOT, ".dotfiles")
BOOTSTRAP_ROOT = os.path.abspath(
    os.environ.get("MIOS_BOOTSTRAP_ROOT") or os.path.join(REPO_ROOT, "..", "mios-bootstrap"))
VENDOR_TOML = os.path.join(REPO_ROOT, "usr/share/mios/mios.toml")

sys.path.insert(0, os.path.join(_HERE_ROOT, "usr/lib/mios"))
import mios_toml  # noqa: E402

VSCODE_SETTINGS_SRC = os.path.join(DOTFILES_DIR, "vscode", "settings.json")
CODESERVER_SETTINGS_SRC = os.path.join(DOTFILES_DIR, "code-server", "settings.json")
CODESERVER_CSS_SRC = os.path.join(DOTFILES_DIR, "code-server", "code-server-terminal.css")

EXIT_DRIFT = 1
EXIT_MISSING_SOURCE = 2
EXIT_BAD_POLICY = 3

# Byte copies: settings FILES a client reads, so they keep the FULL profile
# (an unknown key in a file only warns; ADR-0024).
TARGET_PROJECTIONS = [
    # (source_path, target_rel_path)
    (VSCODE_SETTINGS_SRC, "etc/skel/.vscode/settings.json"),
    (VSCODE_SETTINGS_SRC, "etc/skel/.config/Code/User/settings.json"),
    (VSCODE_SETTINGS_SRC, ".vscode/settings.json"),
    (CODESERVER_SETTINGS_SRC, "etc/skel/.local/share/code-server/User/settings.json"),
    (CODESERVER_SETTINGS_SRC, "usr/share/mios/agents/code-server-mobile-settings.json"),
    (CODESERVER_CSS_SRC, "usr/share/mios/themes/code-server-terminal.css"),
]

# The [dotfiles.vscode] lists, and the ones without which the partition means nothing.
_POLICY_LISTS = ("desktop_only_keys", "user_only_keys", "unregistered_keys",
                 "client_portable_surfaces", "bootstrap_client_portable_surfaces")
_POLICY_REQUIRED = ("desktop_only_keys", "unregistered_keys", "client_portable_surfaces")


def _fatal(msg, code):
    print(f"[sync-dotfiles] FATAL: {msg}", file=sys.stderr)
    return code


def load_policy():
    """mios.toml [dotfiles.vscode] from the vendor tier. Exit 3 on an absent or
    empty partition: no list must never read as "nothing to prune" (ADR-0024)."""
    if not os.path.isfile(VENDOR_TOML):
        raise SystemExit(_fatal(f"vendor SSOT missing: {VENDOR_TOML}", EXIT_MISSING_SOURCE))
    merged = mios_toml.load_merged(layers=[VENDOR_TOML])
    pol = mios_toml.section(merged, "dotfiles.vscode")
    for key in _POLICY_LISTS:
        val = pol.get(key, [])
        if not isinstance(val, list) or not all(isinstance(x, str) and x for x in val):
            raise SystemExit(_fatal(
                f"mios.toml [dotfiles.vscode].{key} must be a list of non-empty strings", EXIT_BAD_POLICY))
    for key in _POLICY_REQUIRED:
        if not pol.get(key):
            raise SystemExit(_fatal(
                f"mios.toml [dotfiles.vscode].{key} is empty or absent -- the client-portable "
                "partition (ADR-0024) cannot be projected without it", EXIT_BAD_POLICY))
    return pol


def pruned_keys(pol):
    """Every key that must not reach a client-portable surface, tagged with WHY
    (the [dotfiles.vscode] list that names it) so a drift line can say so."""
    out = {}
    for key in pol.get("unregistered_keys", []):
        out[key] = "unregistered"
    for key in pol.get("user_only_keys", []):
        out[key] = "User-settings-only (APPLICATION scope)"
    for key in pol.get("desktop_only_keys", []):
        out[key] = "desktop-only"
    return out


def surface_key_path(rel_target):
    """Where the VS Code settings object lives in a surface, decided by the file
    type, not by a per-file literal: customizations.vscode.settings in a
    devcontainer.json, the top-level settings block in a *.code-workspace."""
    if rel_target.endswith(".code-workspace"):
        return ("settings",)
    if os.path.basename(rel_target) == "devcontainer.json":
        return ("customizations", "vscode", "settings")
    raise SystemExit(_fatal(
        f"[dotfiles.vscode] names a surface of unknown type: {rel_target} "
        "(only devcontainer.json and *.code-workspace carry an API-applied settings block)",
        EXIT_BAD_POLICY))


def client_surfaces(pol):
    """[(repo_root, rel_target, key_path, label)] for every client-portable surface
    the SSOT declares: this repository's, then mios-bootstrap's (Law 15)."""
    out = []
    for rel in pol.get("client_portable_surfaces", []):
        out.append((REPO_ROOT, rel, surface_key_path(rel)))
    for rel in pol.get("bootstrap_client_portable_surfaces", []):
        out.append((BOOTSTRAP_ROOT, rel, surface_key_path(rel)))
    return [(root, rel, kp, f"{os.path.basename(os.path.normpath(root))}/{rel}")
            for root, rel, kp in out]


def _get_in(d, path):
    for key in path:
        d = d.setdefault(key, {})
    return d


def _surface_mode(path):
    """The mode a rewritten surface keeps. An existing target keeps its own (a
    devcontainer.json tracked 100755 must not come back 100644); a new one gets
    what a plain open() would give it, 0o666 masked by the process umask."""
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        mask = os.umask(0)
        os.umask(mask)
        return 0o666 & ~mask


def _write_atomic(path, text):
    """Temp file beside the target + rename: a reader never sees a half-written
    surface, and a crash mid-write leaves the committed bytes untouched. The
    temp file takes the target's mode BEFORE the rename: mkstemp creates 0600
    and os.replace carries the temp file's mode, so without this every
    rewritten surface came back 0600 and lost its tracked bit."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    mode = _surface_mode(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=f".{os.path.basename(path)}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _ssot_unregistered(pol, ssot_settings, label):
    """A key VS Code does not know must not sit in the SSOT at all: it would reach
    every byte copy (harmless but dead) and only the prune keeps it off the
    client surfaces. Refuse it at the source."""
    return [(label, f"unregistered key {k} is still in the SSOT -- delete it "
                    "(or drop it from [dotfiles.vscode].unregistered_keys if it came back upstream)")
            for k in pol.get("unregistered_keys", []) if k in ssot_settings]


def project_json_merges(check, pol, ssot_settings):
    """Merge the CLIENT-PORTABLE subset of the SSOT settings into every
    devcontainer.json / *.code-workspace settings block and PRUNE every
    [dotfiles.vscode] desktop-only / User-only / unregistered key already there.
    SSOT keys win on conflict; any surface-only key (installer-specific zenMode.*
    tuning) survives. Returns [(label, reason)] -- one line per key and file, so
    --check names exactly what is wrong where."""
    pruned = pruned_keys(pol)
    portable = {k: v for k, v in ssot_settings.items() if k not in pruned}
    drift = []
    for repo_root, rel_target, key_path, label in client_surfaces(pol):
        dst = os.path.join(repo_root, rel_target)
        if not os.path.isfile(dst):
            if repo_root == REPO_ROOT:
                drift.append((label, "client-portable surface named by [dotfiles.vscode] is missing"))
            # else: degrade open -- the sibling repo is not checked out here
            continue
        with open(dst, "r", encoding="utf-8") as f:
            doc = json.load(f)
        parent = _get_in(doc, key_path[:-1])
        existing = parent.get(key_path[-1], {})
        if not isinstance(existing, dict):
            drift.append((label, f"settings block at {'.'.join(key_path)} is not an object"))
            continue
        expected = {k: v for k, v in existing.items() if k not in pruned}
        expected.update(portable)
        reasons = [f"{pruned[k]} key {k} must not reach a client-portable surface (ADR-0024)"
                   for k in existing if k in pruned]
        for k, v in portable.items():
            if k not in existing:
                reasons.append(f"SSOT key {k} is missing from the surface")
            elif existing[k] != v:
                reasons.append(f"SSOT key {k} differs from the SSOT value")
        if expected != existing and not reasons:
            reasons.append("settings block differs from the SSOT projection")
        drift.extend((label, r) for r in reasons)
        if not check and expected != existing:
            parent[key_path[-1]] = expected
            _write_atomic(dst, json.dumps(doc, indent=2) + "\n")
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize .dotfiles SSOT to system overlays and IDE profiles")
    parser.add_argument("--check", action="store_true", help="Assert projections match SSOT without modifying disk")
    parser.add_argument("--client-surfaces", action="store_true",
                        help="Only the API-applied devcontainer.json / *.code-workspace settings blocks "
                             "(the tracked, drift-gated surfaces); skip the byte copies, mirror and HOME")
    parser.add_argument("--root", default=REPO_ROOT, help="Target repository root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    drift = []

    # 1. Verify source existence
    for src in [VSCODE_SETTINGS_SRC, CODESERVER_SETTINGS_SRC, CODESERVER_CSS_SRC]:
        if not os.path.isfile(src):
            return _fatal(f"Missing SSOT source: {src}", EXIT_MISSING_SOURCE)
    pol = load_policy()
    with open(VSCODE_SETTINGS_SRC, "r", encoding="utf-8") as f:
        vscode_ssot = json.load(f)
    with open(CODESERVER_SETTINGS_SRC, "r", encoding="utf-8") as f:
        codeserver_ssot = json.load(f)
    drift.extend(_ssot_unregistered(pol, vscode_ssot, ".dotfiles/vscode/settings.json"))
    drift.extend(_ssot_unregistered(pol, codeserver_ssot, ".dotfiles/code-server/settings.json"))

    if not args.client_surfaces:
        # 2. Check or project mapped files (byte copies: the full desktop profile)
        for src, rel_target in TARGET_PROJECTIONS:
            dst = os.path.join(root, rel_target)
            src_bytes = open(src, "rb").read()
            if os.path.isfile(dst):
                dst_bytes = open(dst, "rb").read()
                if src_bytes != dst_bytes:
                    drift.append((rel_target, "byte copy differs from the SSOT source"))
            else:
                drift.append((rel_target, "byte copy is missing"))

            if not args.check:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    f.write(src_bytes)

        # 3. Mirror .dotfiles to usr/share/mios/dotfiles
        share_dotfiles = os.path.join(root, "usr/share/mios/dotfiles")
        if not args.check:
            os.makedirs(share_dotfiles, exist_ok=True)
            for dirpath, _, filenames in os.walk(DOTFILES_DIR):
                rel = os.path.relpath(dirpath, DOTFILES_DIR)
                target_dir = os.path.join(share_dotfiles, rel) if rel != "." else share_dotfiles
                os.makedirs(target_dir, exist_ok=True)
                for fn in filenames:
                    s_file = os.path.join(dirpath, fn)
                    d_file = os.path.join(target_dir, fn)
                    shutil.copy2(s_file, d_file)

        # 4. Also project into active user home directories if write mode
        if not args.check:
            home = os.environ.get("HOME", "")
            if home and os.path.isdir(home):
                home_targets = [
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".config/Code/User/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-server/data/Machine/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-server/data/User/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-remote/data/Machine/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-remote/data/User/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-server-insiders/data/Machine/settings.json")),
                    (VSCODE_SETTINGS_SRC, os.path.join(home, ".vscode-server-insiders/data/User/settings.json")),
                    (CODESERVER_SETTINGS_SRC, os.path.join(home, ".local/share/code-server/User/settings.json")),
                ]
                for s, d in home_targets:
                    if os.path.isdir(os.path.dirname(d)):
                        try:
                            shutil.copy2(s, d)
                        except Exception:
                            pass
            # Sync theme extension to skeletons and home profiles
            theme_src = os.path.join(root, "usr/share/mios/extensions/mios-theme-mobile")
            if os.path.isdir(theme_src):
                skel_targets = [
                    os.path.join(root, "etc/skel/.vscode/extensions/mios-theme-mobile"),
                    os.path.join(root, "etc/skel/.local/share/code-server/extensions/mios-theme-mobile"),
                ]
                for st in skel_targets:
                    try:
                        os.makedirs(os.path.dirname(st), exist_ok=True)
                        if os.path.exists(st):
                            if os.path.islink(st):
                                os.unlink(st)
                            elif os.path.isdir(st):
                                shutil.rmtree(st)
                        shutil.copytree(theme_src, st)
                    except Exception:
                        pass

                home = os.environ.get("HOME", "")
                if home and os.path.isdir(home):
                    user_ext_targets = [
                        os.path.join(home, ".vscode-server/extensions/mios-theme-mobile"),
                        os.path.join(home, ".vscode-server-insiders/extensions/mios-theme-mobile"),
                        os.path.join(home, ".vscode-remote/extensions/mios-theme-mobile"),
                        os.path.join(home, ".vscode-remote-insiders/extensions/mios-theme-mobile"),
                        os.path.join(home, ".local/share/code-server/extensions/mios-theme-mobile"),
                    ]
                    for ut in user_ext_targets:
                        try:
                            if os.path.isdir(os.path.dirname(ut)):
                                if os.path.exists(ut):
                                    if os.path.islink(ut):
                                        os.unlink(ut)
                                    elif os.path.isdir(ut):
                                        shutil.rmtree(ut)
                                shutil.copytree(theme_src, ut)
                        except Exception:
                            pass

            if os.access("/usr/share/mios/themes", os.W_OK):
                try:
                    shutil.copy2(CODESERVER_CSS_SRC, "/usr/share/mios/themes/code-server-terminal.css")
                except Exception:
                    pass

    # 5. Merge the client-portable SSOT subset into every devcontainer.json /
    #    *.code-workspace and prune what a connecting client may not register.
    drift.extend(project_json_merges(args.check, pol, vscode_ssot))

    if args.check:
        if drift:
            for label, reason in drift:
                print(f"[sync-dotfiles] DRIFT {label}: {reason}", file=sys.stderr)
            files = sorted({label for label, _ in drift})
            print(f"[sync-dotfiles] Drift detected in {len(files)} files: {', '.join(files)}", file=sys.stderr)
            return EXIT_DRIFT
        print("[sync-dotfiles] All .dotfiles projections in sync.")
        return 0

    # Write mode: the SSOT itself carrying a key VS Code does not know is the one
    # drift the projection cannot repair, so it is reported and fails the run.
    unfixable = [(label, reason) for label, reason in drift
                 if label.startswith(".dotfiles/") and reason.startswith("unregistered key")]
    if unfixable:
        for label, reason in unfixable:
            print(f"[sync-dotfiles] DRIFT {label}: {reason}", file=sys.stderr)
        return EXIT_DRIFT
    what = ("the client-portable surfaces" if args.client_surfaces
            else f"{len(TARGET_PROJECTIONS)} targets + the client-portable surfaces")
    print(f"[sync-dotfiles] Successfully synchronized .dotfiles SSOT to {what}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

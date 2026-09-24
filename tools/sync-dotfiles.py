#!/usr/bin/env python3
# AI-hint: Synchronizes .dotfiles SSOT into all IDE profiles, skeletons, and themes (T-532, AGY-2130).
# AI-doc: usr/share/doc/mios/manual/tools.md
import argparse
import json
import os
import shutil
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOTFILES_DIR = os.path.join(REPO_ROOT, ".dotfiles")
BOOTSTRAP_ROOT = os.path.abspath(os.path.join(REPO_ROOT, "..", "mios-bootstrap"))

VSCODE_SETTINGS_SRC = os.path.join(DOTFILES_DIR, "vscode", "settings.json")
CODESERVER_SETTINGS_SRC = os.path.join(DOTFILES_DIR, "code-server", "settings.json")
CODESERVER_CSS_SRC = os.path.join(DOTFILES_DIR, "code-server", "code-server-terminal.css")

TARGET_PROJECTIONS = [
    # (source_path, target_rel_path, is_dir_or_file)
    (VSCODE_SETTINGS_SRC, "etc/skel/.vscode/settings.json"),
    (VSCODE_SETTINGS_SRC, "etc/skel/.config/Code/User/settings.json"),
    (VSCODE_SETTINGS_SRC, ".vscode/settings.json"),
    (CODESERVER_SETTINGS_SRC, "etc/skel/.local/share/code-server/User/settings.json"),
    (CODESERVER_SETTINGS_SRC, "usr/share/mios/agents/code-server-mobile-settings.json"),
    (CODESERVER_CSS_SRC, "usr/share/mios/themes/code-server-terminal.css"),
]

# Every devcontainer.json / *.code-workspace whose embedded VS Code settings
# object must be kept in lockstep with the .dotfiles SSOT (ADR-0010). Each
# entry is (repo_root, target_rel_path, key_path_into_the_settings_object).
# The projection is a MERGE, not an overwrite: SSOT keys win on conflict, but
# any surface-only key (e.g. installer-specific zenMode.* tuning) survives.
JSON_MERGE_PROJECTIONS = [
    (REPO_ROOT, ".devcontainer/devcontainer.json", ("customizations", "vscode", "settings")),
    (REPO_ROOT, ".devcontainer/artifact-builder/devcontainer.json", ("customizations", "vscode", "settings")),
    (REPO_ROOT, "mios.code-workspace", ("settings",)),
    (REPO_ROOT, ".devcontainer/mios-ecosystem.code-workspace", ("settings",)),
    (BOOTSTRAP_ROOT, ".devcontainer/devcontainer.json", ("customizations", "vscode", "settings")),
]


def _get_in(d, path):
    for key in path:
        d = d.setdefault(key, {})
    return d


def _project_json_merges(check):
    """Merge the SSOT vscode settings dict into every devcontainer.json/*.code-workspace."""
    ssot_settings = json.loads(open(VSCODE_SETTINGS_SRC, "r", encoding="utf-8").read())
    drift = []
    for repo_root, rel_target, key_path in JSON_MERGE_PROJECTIONS:
        dst = os.path.join(repo_root, rel_target)
        label = f"{os.path.basename(os.path.normpath(repo_root))}/{rel_target}"
        if not os.path.isfile(dst):
            continue  # degrade open: sibling repo/profile not checked out here
        with open(dst, "r", encoding="utf-8") as f:
            doc = json.load(f)
        parent = _get_in(doc, key_path[:-1])
        existing = parent.get(key_path[-1], {})
        merged = dict(existing)
        merged.update(ssot_settings)
        if merged != existing:
            drift.append(label)
        if not check:
            parent[key_path[-1]] = merged
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
                f.write("\n")
    return drift

def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize .dotfiles SSOT to system overlays and IDE profiles")
    parser.add_argument("--check", action="store_true", help="Assert projections match SSOT without modifying disk")
    parser.add_argument("--root", default=REPO_ROOT, help="Target repository root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    drift = []

    # 1. Verify source existence
    for src in [VSCODE_SETTINGS_SRC, CODESERVER_SETTINGS_SRC, CODESERVER_CSS_SRC]:
        if not os.path.isfile(src):
            print(f"[sync-dotfiles] ERROR: Missing SSOT source: {src}", file=sys.stderr)
            return 2

    # 2. Check or project mapped files
    for src, rel_target in TARGET_PROJECTIONS:
        dst = os.path.join(root, rel_target)
        src_bytes = open(src, "rb").read()
        if os.path.isfile(dst):
            dst_bytes = open(dst, "rb").read()
            if src_bytes != dst_bytes:
                drift.append(rel_target)
        else:
            drift.append(rel_target)

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

    # 5. Merge the SSOT settings into every devcontainer.json / *.code-workspace
    drift.extend(_project_json_merges(args.check))

    if args.check:
        if drift:
            print(f"[sync-dotfiles] Drift detected in {len(drift)} files: {', '.join(drift)}", file=sys.stderr)
            return 1
        print("[sync-dotfiles] All .dotfiles projections in sync.")
        return 0

    print(f"[sync-dotfiles] Successfully synchronized .dotfiles SSOT to {len(TARGET_PROJECTIONS)} targets.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

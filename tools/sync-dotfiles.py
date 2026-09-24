#!/usr/bin/env python3
# AI-hint: Synchronizes .dotfiles SSOT into all IDE profiles, skeletons, and themes (T-532, AGY-2130).
# AI-doc: usr/share/doc/mios/manual/tools.md
import argparse
import os
import shutil
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOTFILES_DIR = os.path.join(REPO_ROOT, ".dotfiles")

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
        if os.access("/usr/share/mios/themes", os.W_OK):
            try:
                shutil.copy2(CODESERVER_CSS_SRC, "/usr/share/mios/themes/code-server-terminal.css")
            except Exception:
                pass

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

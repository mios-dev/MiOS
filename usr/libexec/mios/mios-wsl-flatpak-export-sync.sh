#!/usr/bin/env bash
# /usr/libexec/mios/mios-wsl-flatpak-export-sync.sh
#
# Mirror flatpak's `.desktop` + icon exports into the system XDG dirs so
# WSL2's Start Menu app sync can see them. Operator-flagged 2026-05-11
# "no icons match and all apps aren't populating in windows NATIVELY".
#
# Why WSL2 needs this: the wsl.exe distro launcher scans .desktop files
# under /usr/share/applications/ (and ~/.local/share/applications/) and
# auto-creates Windows Start Menu .lnk shortcuts under
# %APPDATA%\Microsoft\Windows\Start Menu\Programs\<distro>\. Flatpak
# installs every .desktop under /var/lib/flatpak/exports/share/, which
# wsl.exe does NOT scan. Symlinking the exports into /usr/share/ on
# each boot is the cheapest way to surface flatpak apps to Windows.
#
# What this script does:
#   1. Symlink every /var/lib/flatpak/exports/share/applications/*.desktop
#      into /usr/share/applications/  (skip duplicates).
#   2. Symlink the entire flatpak icons hicolor tree into
#      /usr/share/icons/hicolor/ at the SIZE+CATEGORY level, so apps
#      whose .desktop says `Icon=org.gnome.Epiphany` resolve to the
#      flatpak-shipped PNG/SVG.
#   3. Refresh icon caches (gtk-update-icon-cache + update-desktop-database)
#      so the symlinks register immediately.
#
# Idempotent: re-runs are no-ops if every link already points at the
# right target. Run as ExecStart of mios-wsl-flatpak-export-sync.service
# (boot + flatpak-install path-changed trigger).

set -euo pipefail

_log() { echo "[wsl-flatpak-export-sync] $*" >&2; }

FLATPAK_APPS=/var/lib/flatpak/exports/share/applications
FLATPAK_ICONS=/var/lib/flatpak/exports/share/icons
SYS_APPS=/usr/share/applications
SYS_ICONS=/usr/share/icons

if [[ ! -d "$FLATPAK_APPS" ]]; then
    _log "no flatpak exports dir at $FLATPAK_APPS -- skipping"
    exit 0
fi

install -d -m 0755 "$SYS_APPS" "$SYS_ICONS"

# 1. Mirror .desktop files. Use symlinks so a flatpak uninstall removes
# the dangling link on the next sync (we GC stale links below).
mirrored=0
for src in "$FLATPAK_APPS"/*.desktop; do
    [[ -f "$src" ]] || continue
    base="$(basename "$src")"
    dst="$SYS_APPS/$base"
    # Skip if a NATIVE non-symlink already provides this app (don't shadow
    # an RPM-installed .desktop with the flatpak one; flatpak ships the
    # alternative app under .Devel or .ChromeDev suffix anyway).
    if [[ -e "$dst" && ! -L "$dst" ]]; then
        continue
    fi
    if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
        continue
    fi
    ln -sf "$src" "$dst"
    mirrored=$((mirrored + 1))
done
_log "mirrored $mirrored flatpak .desktop entries -> $SYS_APPS"

# 2. Mirror icons. hicolor is the canonical icon theme that every
# .desktop's Icon= resolves through. flatpak exports its icons under
# /var/lib/flatpak/exports/share/icons/hicolor/<size>/apps/, matching
# the standard XDG layout.
if [[ -d "$FLATPAK_ICONS/hicolor" ]]; then
    install -d -m 0755 "$SYS_ICONS/hicolor"
    icons_mirrored=0
    # `find -L` follows symlinks: flatpak's hicolor/scalable/apps/*.svg
    # entries are symlinks into /var/lib/flatpak/app/<id>/current/...
    # which `-type f` (no -L) rejects. With -L, find resolves them and
    # the -type f predicate matches the target regular file.
    while IFS= read -r -d '' iconfile; do
        rel="${iconfile#$FLATPAK_ICONS/}"     # e.g. "hicolor/scalable/apps/com.google.ChromeDev.svg"
        dst="$SYS_ICONS/$rel"
        if [[ -e "$dst" && ! -L "$dst" ]]; then continue; fi
        if [[ -L "$dst" && "$(readlink "$dst")" == "$iconfile" ]]; then continue; fi
        install -d -m 0755 "$(dirname "$dst")"
        ln -sf "$iconfile" "$dst"
        icons_mirrored=$((icons_mirrored + 1))
    done < <(find -L "$FLATPAK_ICONS/hicolor" -type f \( -name '*.png' -o -name '*.svg' -o -name '*.xpm' \) -print0)
    _log "mirrored $icons_mirrored flatpak icon files -> $SYS_ICONS/hicolor"
fi

# 3. GC stale symlinks (flatpak uninstall left behind).
gc=0
for link in "$SYS_APPS"/*.desktop; do
    [[ -L "$link" ]] || continue
    target="$(readlink "$link")"
    if [[ "$target" == "$FLATPAK_APPS/"* && ! -e "$target" ]]; then
        rm -f "$link"
        gc=$((gc + 1))
    fi
done
[[ $gc -gt 0 ]] && _log "GC: removed $gc stale flatpak .desktop links"

# 4. Refresh caches so the desktop databases see the new entries.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q "$SYS_APPS" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f "$SYS_ICONS/hicolor" 2>/dev/null || true
fi

_log "done"

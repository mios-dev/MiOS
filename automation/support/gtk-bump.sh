#!/bin/bash
# AI-hint: Script to resolve stale GNOME 49 flatpak runtimes by adding the flathub-beta remote and identifying newer GNOME 50 builds for specific apps like Ptyxis and Flatseal.
# Try to bump GNOME 49-stuck flatpaks to GNOME 50 by switching to
# flathub-beta (or flathub) where the upstream maintainer has
# published a newer build. Operator-flagged 2026-05-19 "GLOBAL GTK
# IS OLD STILL".
set -euo pipefail

echo "== current remotes =="
flatpak remotes 2>&1
echo

echo "== ensure flathub-beta remote present =="
if ! flatpak remotes | grep -q flathub-beta; then
    sudo flatpak remote-add --if-not-exists flathub-beta \
        https://flathub.org/beta-repo/flathub-beta.flatpakrepo 2>&1 | head -3
fi
echo

echo "== check what newer branches exist for the stuck apps =="
for app in app.devsuite.Ptyxis com.github.tchx84.Flatseal; do
    echo "--- $app ---"
    echo "  installed: $(flatpak info "$app" 2>&1 | grep -E 'Branch:|Runtime:' | tr -d '\n')"
    echo "  flathub:       $(flatpak remote-info flathub "$app" 2>&1 | grep -E 'Branch:|Runtime:' | tr -d '\n')"
    echo "  flathub-beta:  $(flatpak remote-info flathub-beta "$app" 2>&1 | grep -E 'Branch:|Runtime:' | tr -d '\n')"
done
echo

echo "== look for any GNOME Platform 50 apps available in flathub --"
flatpak remote-ls --columns=application,branch flathub 2>/dev/null | grep -E "^app.devsuite.Ptyxis|^com.github.tchx84.Flatseal" | head -10

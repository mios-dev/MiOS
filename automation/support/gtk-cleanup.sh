#!/bin/bash
# AI-hint: Audits and cleans up GTK/GNOME runtimes by identifying stale Platform 49 versions, forcing flatpak updates, and purging unused runtimes to ensure a clean, up-to-date desktop environment.
set -euo pipefail

echo "== apps running on GNOME Platform 49 =="
for app in $(flatpak list --app --columns=application 2>/dev/null); do
    rt=$(flatpak info "$app" 2>/dev/null | grep -E "^ *Runtime:" | awk '{print $2}')
    case "$rt" in
        *org.gnome.Platform/x86_64/49*) echo "  $app -> $rt" ;;
    esac
done
echo

echo "== apps on master =="
for app in $(flatpak list --app --columns=application 2>/dev/null); do
    rt=$(flatpak info "$app" 2>/dev/null | grep -E "^ *Runtime:" | awk '{print $2}')
    case "$rt" in
        *master*) echo "  $app -> $rt" ;;
    esac
done
echo

echo "== apps on stable / 50 =="
for app in $(flatpak list --app --columns=application 2>/dev/null); do
    rt=$(flatpak info "$app" 2>/dev/null | grep -E "^ *Runtime:" | awk '{print $2}')
    case "$rt" in
        *org.gnome.Platform/x86_64/50*|*stable*) echo "  $app -> $rt" ;;
    esac
done
echo

echo "== full flatpak update =="
sudo flatpak update --noninteractive --assumeyes 2>&1 | tail -30
echo

echo "== uninstall unused runtimes =="
sudo flatpak uninstall --unused --noninteractive --assumeyes 2>&1 | tail -10
echo

echo "== final runtime tally =="
flatpak list --runtime --columns=application,branch,version 2>/dev/null | grep -E "Platform|Sdk|adw" | head -15

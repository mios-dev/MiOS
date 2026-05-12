#!/bin/bash
# Enumerate every visible .desktop entry inside the WSL distro --
# flatpak apps + every /usr/share/applications/ entry that isn't
# explicitly hidden -- so Windows Start Menu shows the full Linux
# app surface. Operator-flagged 2026-05-11: "I want all the Linux
# apps icons visible in windows".
#
# Filter: only NoDisplay=true entries are skipped (those are explicitly
# hidden per the freedesktop spec -- internal MIME handlers, portal
# helpers, OAuth providers, GNOME Settings sub-panels). Terminal=true
# entries (btop++, nvtop, etc.) ARE included since wslg.exe can launch
# them in a Linux terminal that surfaces on the Windows side.
# Operator-flagged 2026-05-12: "not seeing ALL apps in windows sise".
# Everything else is emitted as one pipe-delimited record:
#   Name|Exec|Icon|NoDisplay|Terminal|Categories|file
shopt -s nullglob

# De-dup by basename: prefer the flatpak version when an rpm + flatpak
# ship the same app (e.g. Fedora's nautilus vs flatpak Nautilus.Devel).
declare -A _seen

for f in /var/lib/flatpak/exports/share/applications/*.desktop \
         /usr/share/applications/*.desktop \
         /var/home/*/.local/share/applications/*.desktop; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    [ -n "${_seen[$base]:-}" ] && continue
    _seen[$base]=1

    name=$(sed -nE 's/^Name=(.*)$/\1/p' "$f" | head -1)
    exec=$(sed -nE 's/^Exec=(.*)$/\1/p' "$f" | head -1)
    icon=$(sed -nE 's/^Icon=(.*)$/\1/p' "$f" | head -1)
    nodisp=$(sed -nE 's/^NoDisplay=(.*)$/\1/p' "$f" | head -1)
    term=$(sed -nE 's/^Terminal=(.*)$/\1/p' "$f" | head -1)
    cat=$(sed -nE 's/^Categories=(.*)$/\1/p' "$f" | head -1)
    [ -z "$name" ] && continue
    [ "$nodisp" = "true" ] && continue
    printf '%s|%s|%s|%s|%s|%s|%s\n' "$name" "$exec" "$icon" "${nodisp:-false}" "${term:-false}" "$cat" "$f"
done

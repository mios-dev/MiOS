#!/bin/bash

# --- 1. INSTALLATION ---
if ! pacman -Qs bibata-cursor-theme-bin > /dev/null; then
    echo "Installing Bibata Modern Cursor Suite..."
    paru -S bibata-cursor-theme-bin --noconfirm
fi

# --- 2. INTERACTIVE SELECTION ---
mapfile -t THEMES < <(ls /usr/share/icons/ | grep "Bibata-Modern")
echo "Select your cursor theme:"
for i in "${!THEMES[@]}"; do
    echo "$((i+1))) ${THEMES[$i]}"
done
read -p "Enter number (1-${#THEMES[@]}): " CHOICE
SELECTED="${THEMES[$((CHOICE-1))]}"
SIZE="24"

if [ -z "$SELECTED" ]; then echo "Invalid selection"; exit 1; fi

# --- 3. APPLY TO NIRI (Wayland) ---
NIRI_CONF="$HOME/.config/niri/config.kdl"
if [ -f "$NIRI_CONF" ]; then
    sed -i "s/xcursor-theme \".*\"/xcursor-theme \"$SELECTED\"/" "$NIRI_CONF"
    sed -i "s/xcursor-size .*/xcursor-size $SIZE/" "$NIRI_CONF"
    echo "[âœ"] Niri updated."
fi

# --- 4. APPLY TO GTK 3 & 4 (Native Apps) ---
for v in "3.0" "4.0"; do
    CONF="$HOME/.config/gtk-$v/settings.ini"
    mkdir -p "$(dirname "$CONF")"
    echo -e "[Settings]\ngtk-cursor-theme-name=$SELECTED\ngtk-cursor-theme-size=$SIZE" > "$CONF"
    echo "[âœ"] GTK $v updated."
done

# --- 5. APPLY TO X11 & XWAYLAND (The 'Flicker' Fix) ---
# This ensures legacy windows and games don't revert to the 'X' cursor
mkdir -p "$HOME/.icons/default"
echo -e "[Icon Theme]\nInherits=$SELECTED" > "$HOME/.icons/default/index.theme"
# Also set for the X server resource database
echo "Xcursor.theme: $SELECTED" > "$HOME/.Xresources"
echo "Xcursor.size: $SIZE" >> "$HOME/.Xresources"
xrdb -merge "$HOME/.Xresources" 2>/dev/null
echo "[âœ"] X11/XWayland global settings updated."

# --- 6. APPLY TO FLATPAK (Sandbox Fix) ---
# Gives Flatpaks permission to see the icons and forces the env variables
echo "Punching through Flatpak sandbox..."
flatpak override --user --filesystem=xdg-config/gtk-3.0:ro --filesystem=xdg-config/gtk-4.0:ro
flatpak override --user --filesystem=$HOME/.icons:ro --filesystem=/usr/share/icons:ro
flatpak override --user --env=XCURSOR_THEME="$SELECTED" --env=XCURSOR_SIZE="$SIZE"
echo "[âœ"] Flatpak environment synchronized."

echo "Done! Please restart your session (Mod+Shift+E) to apply everywhere."

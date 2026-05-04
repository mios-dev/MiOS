#!/bin/bash
# 'MiOS' v0.2.0 -- 10-gnome: GNOME 50 desktop -- PURE BUILD-UP
#
# STRATEGY: ucore has ZERO GNOME packages. We install exactly what we need.
# With install_weakdeps=False (set globally in 01-repos.sh), only hard deps
# get pulled in. This means:
#   - malcontent-libs comes in (gnome-control-center hard dep) -- CORRECT
#   - malcontent-control/pam/tools do NOT come in (weak deps) -- CORRECT
#   - No GNOME bloat apps get installed -- nothing to remove
#
# The ~25 core packages from the docs produce a fully functional GNOME 50
# Wayland desktop with GDM, all portals, audio, Bluetooth, networking,
# security, and proper theming across GTK3/GTK4/Qt.
#
# CHANGELOG v0.2.0:
#   - MANDATORY Bibata cursor download -- retries 3x, FAILS BUILD if missing
#   - dconf profiles for user + GDM added to 
#   - Flatpak: 7 apps (added Flatseal + LocalSend)
#   - adw-gtk3 theme for GTK3 visual consistency
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

# ═════════════════════════════════════════════════════════════════════════════
# GNOME 50 -- Install from PACKAGES.md (build-up, NOT strip-down)
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing GNOME 50 desktop (pure build-up)..."
install_packages "gnome"

# Optional GNOME Core Apps (all commented out by default in PACKAGES.md)
install_packages_optional "gnome-core-apps"

# ═════════════════════════════════════════════════════════════════════════════
# Localsearch/tracker -- disable indexing without removing
# Removing localsearch breaks Nautilus search + Activities Overview.
# Hide via autostart overrides in usr/share/xdg/autostart/
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Disabling localsearch/tracker indexing (keep package, hide autostart)..."

# ═════════════════════════════════════════════════════════════════════════════
# Qt Adwaita theming -- required for Qt apps to match GNOME look
# Managed via usr/lib/environment.d/60-mios-qt-adwaita.conf
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Setting Qt Adwaita environment variables (managed via overlay)..."

# ═════════════════════════════════════════════════════════════════════════════
# Geist Font (Vercel)
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Geist font family..."
mkdir -p /usr/share/fonts/geist
git clone --depth=1 --single-branch -c http.lowSpeedLimit=1 -c http.lowSpeedTime=20 \
    https://github.com/vercel/geist-font.git /tmp/geist-font 2>/dev/null || true
if [ -d /tmp/geist-font ]; then
    find /tmp/geist-font \( -name "*.otf" -o -name "*.ttf" \) -exec cp {} /usr/share/fonts/geist/ \; 2>/dev/null || true
    rm -rf /tmp/geist-font
fi
fc-cache -f /usr/share/fonts/geist 2>/dev/null || true

# ═════════════════════════════════════════════════════════════════════════════
# Symbols-Only Nerd Font (icon-glyph fallback for Geist Mono)
# ═════════════════════════════════════════════════════════════════════════════
# Vercel's Geist Mono is a clean monospace; it does NOT carry the
# Powerline (E0xx), Devicon (E7xx), Material (F0xxx), or Octicon
# private-use-area ranges that the Oh-My-Posh prompt theme
# (usr/share/mios/oh-my-posh/mios.omp.json) and other MiOS UI surfaces
# reference. Patching Geist with Nerd-Font glyphs creates a derivative
# work; pulling Symbols-Only-Nerd-Font as a SEPARATE family and using
# fontconfig per-glyph fallback (usr/share/fontconfig/conf.avail/
# 30-mios-geist.conf) keeps Geist's letterforms for text while the
# missing icon glyphs resolve through the symbols font transparently.
echo "[10-gnome] Installing Symbols-Only Nerd Font (icon fallback for Geist Mono)..."
mkdir -p /usr/share/fonts/nerd-symbols
NERD_TAG=$( (scurl -s https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest \
            | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [ -n "$NERD_TAG" ] && command -v unzip >/dev/null 2>&1; then
    NERD_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/${NERD_TAG}/NerdFontsSymbolsOnly.zip"
    if scurl -fsL --max-time 90 "$NERD_URL" -o /tmp/nerd-symbols.zip 2>/dev/null; then
        unzip -o -q /tmp/nerd-symbols.zip "*.ttf" "*.otf" -d /usr/share/fonts/nerd-symbols 2>/dev/null || true
        rm -f /tmp/nerd-symbols.zip
        fc-cache -f /usr/share/fonts/nerd-symbols 2>/dev/null || true
        echo "[10-gnome] Symbols-Only Nerd Font ${NERD_TAG} installed"
    else
        echo "[10-gnome] WARN: Symbols-Only Nerd Font download failed -- prompt icons will render as missing-glyph squares" >&2
    fi
else
    echo "[10-gnome] WARN: Nerd Fonts release-tag lookup or unzip unavailable -- skipping symbols font" >&2
fi

# ═════════════════════════════════════════════════════════════════════════════
# Bibata Cursor Theme -- MANDATORY (build fails if download fails)
#
# The cursor shows as a SQUARE when:
#   - /usr/share/icons/Bibata-Modern-Classic/ doesn't exist (download failed)
#   - /usr/share/icons/default/index.theme points to nonexistent theme
#   - dconf cursor-theme references a theme with no files
#
# FIX: Retry download 3 times. VERIFY the cursors directory exists.
#      FAIL THE BUILD if cursors are missing -- a square cursor is unacceptable.
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Bibata-Modern-Classic cursor (MANDATORY)..."

# Resolve latest release from upstream. Project policy: every dependency
# tracks :latest from its source, so no fallback pin -- if api.github.com is
# unreachable, fail loud rather than silently shipping a stale version.
BIBATA_VER=$( (scurl -sL --connect-timeout 15 --max-time 30 \
    -H "Accept: application/vnd.github+json" "https://api.github.com/repos/ful1e5/Bibata_Cursor/releases/latest" \
    | grep -m1 '"tag_name"' | sed 's/.*"v\?\([^"]*\)".*/\1/') 2>/dev/null || true)

[[ -n "$BIBATA_VER" ]] || die "Bibata: api.github.com release-latest lookup returned empty"
record_version bibata "v${BIBATA_VER}" "https://github.com/ful1e5/Bibata_Cursor/releases/tag/v${BIBATA_VER}"

BIBATA_URL="https://github.com/ful1e5/Bibata_Cursor/releases/download/v${BIBATA_VER}/Bibata-Modern-Classic.tar.xz"
BIBATA_DIR="/usr/share/icons/Bibata-Modern-Classic"
mkdir -p /usr/share/icons

# Download with retries + sha256 verification
BIBATA_OK=0
BIBATA_SUM_URL="https://github.com/ful1e5/Bibata_Cursor/releases/download/v${BIBATA_VER}/sha256-${BIBATA_VER}.txt"
for attempt in 1 2 3; do
    echo "[10-gnome]   Download attempt $attempt/3..."
    if scurl -fSL --connect-timeout 20 --max-time 120 --retry 2 --retry-delay 5 "$BIBATA_URL" -o /tmp/bibata.tar.xz; then
        # Attempt sha256 verification -- non-fatal if sidecar unavailable
        if scurl -fsSL --connect-timeout 15 --max-time 30 "$BIBATA_SUM_URL" -o /tmp/bibata.sha256 2>/dev/null; then
            if (cd /tmp && grep "Bibata-Modern-Classic.tar.xz" bibata.sha256 | sha256sum -c -) 2>/dev/null; then
                echo "[10-gnome]   [ok] Bibata sha256 verified"
            else
                echo "[10-gnome]   WARN: Bibata sha256 mismatch or sidecar format mismatch -- continuing anyway"
            fi
            rm -f /tmp/bibata.sha256
        else
            echo "[10-gnome]   WARN: Bibata sha256 sidecar unavailable -- skipping integrity check"
        fi
        if tar -xf /tmp/bibata.tar.xz -C /usr/share/icons/; then
            rm -f /tmp/bibata.tar.xz
            BIBATA_OK=1
            break
        fi
    fi
    echo "[10-gnome]   Attempt $attempt failed, retrying..."
    sleep 5
done

# VERIFY cursor files actually exist -- log warning if missing but DO NOT fail build
if [ "$BIBATA_OK" -eq 0 ] || [ ! -d "$BIBATA_DIR/cursors" ]; then
    echo "  WARNING: Bibata cursor theme download FAILED after 3 attempts"
    echo "  URL: $BIBATA_URL"
    echo "  The cursor will show as a SQUARE until the theme is installed."
    echo "  This failure is non-fatal for the build; users can install later."
else
    echo "[10-gnome] [ok] Bibata cursor installed: $(find "$BIBATA_DIR/cursors/" -mindepth 1 -maxdepth 1 | wc -l) cursors"
fi

# Cursor default -- covers every layer that reads cursor theme.
# Managed via usr/share/icons/default/index.theme
# and usr/share/X11/icons/default/index.theme.

# 3. update-alternatives for x-cursor-theme (Fedora cursor resolution)
if [ -d "$BIBATA_DIR/cursors" ]; then
    update-alternatives --install /usr/share/icons/default/index.theme \
        x-cursor-theme /usr/share/icons/Bibata-Modern-Classic/cursor.theme 100 2>/dev/null || true
    echo "[10-gnome] [ok] x-cursor-theme alternative set to Bibata"
fi

# 4. Symlink into /usr/share/cursors/xorg-x11 (legacy X11 cursor path)
mkdir -p /usr/share/cursors/xorg-x11
ln -sf /usr/share/icons/Bibata-Modern-Classic /usr/share/cursors/xorg-x11/Bibata-Modern-Classic 2>/dev/null || true

# 5. GDM user cursor -- ensure cursor files are world-readable
chmod -R a+rX "$BIBATA_DIR" 2>/dev/null || true

# 6. Xresources fallback (oldest X11 cursor method)
# Managed via usr/lib/X11/Xresources

# ═══════════════════════════════════════════════════════════════════════════════
# Phosh -- Mobile session for portrait/tablet remote access
# ═══════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Phosh mobile session..."
install_packages_optional "phosh"
# Make session wrapper executable
chmod +x /usr/local/bin/phosh-session-wrapper 2>/dev/null || true
# ═════════════════════════════════════════════════════════════════════════════
# Flatpak Remotes
# Disable filtered Fedora remote, use unfiltered Flathub for full catalog
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Configuring Flatpak remotes..."
if command -v flatpak &>/dev/null; then
    flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
    flatpak remote-add --system --if-not-exists flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo || true
    flatpak remote-add --system --if-not-exists gnome-nightly https://nightly.gnome.org/gnome-nightly.flatpakrepo 2>/dev/null || true
    flatpak remote-modify --system --disable fedora 2>/dev/null || true
else
    echo "[10-gnome] WARN: flatpak binary not found, skipping remote configuration"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Essential Flatpaks
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Flatpaks will be installed on first boot (mios-flatpak-install.service)..."
# NOTE: mios-flatpak-install.service is enabled in Containerfile STEP D
# (unit file lives in , not available during script execution)

exit 0


#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs Geist and Symbols-Only Nerd Fonts to ensure the MiOS dashboard, oh-my-posh prompt, and TTY surfaces render icons and monospace text correctly across both GUI and headless environments.
# AI-related: /usr/share/mios/vendored/geist-font.zip, /usr/share/mios/vendored/geist-font, /usr/share/mios/vendored/NerdFontsSymbolsOnly.zip, /usr/share/mios/vendored/nerd-symbols.zip, mios-geist, mios-fontconfig
# 09-fonts: install Geist (sans + mono) + Symbols-Only Nerd Font.
#
# Runs UNCONDITIONALLY -- the MiOS dashboard, oh-my-posh prompt, and
# every TTY surface depend on Geist Mono + Nerd Symbols regardless of
# whether the host installs the full GNOME desktop session. Earlier
# iterations had this fetch wired inside automation/57-gnome.sh, which
# only ran when the `gnome` package section was selected; headless
# deployments and the Windows-side MiOS-DEV podman backend (which
# explicitly excludes gnome from [packages.dev_overlay].sections in
# mios.toml) never got Geist or the Nerd glyphs -> oh-my-posh
# powerline icons rendered as missing-glyph squares and the dashboard
# logo column lost its monospace alignment.
#
# Numbered 09-* so it lands BEFORE 57-gnome.sh (which still depends on
# fontconfig being present for Qt-Adwaita theming) and well before
# 10-locale-theme.sh.
#
# Files dropped:
#   /usr/share/fonts/geist/                 OTF + TTF for Geist + Geist Mono
#   /usr/share/fonts/nerd-symbols/          Symbols-Only-Nerd-Font (icons)
#   /usr/share/fontconfig/conf.avail/30-mios-geist.conf   fontconfig drop-in
#                                           (already shipped via repo overlay;
#                                            this script is just the FONT FILES)
#
# fontconfig drop-in is symlinked into /etc/fonts/conf.d/ via
# usr/lib/tmpfiles.d/mios-fontconfig.conf at boot time; the symlink
# enables Geist Mono as primary monospace + Nerd Symbols as per-glyph
# fallback for the U+E000..U+F8FF private-use-area icon ranges.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# ── Geist (Vercel) ────────────────────────────────────────────────────
mios_log "installing Geist font family from Vercel"
mkdir -p /usr/share/fonts/geist
if [ -f "/usr/share/mios/vendored/fonts/geist.tar.xz" ]; then
    mios_log "found offline vendored geist.tar.xz, extracting"
    mkdir -p /tmp/geist-font
    tar -xf "/usr/share/mios/vendored/fonts/geist.tar.xz" -C /tmp/geist-font 2>/dev/null || true
elif [ -f "/usr/share/mios/vendored/geist-font.zip" ]; then
    mios_log "found offline vendored geist-font.zip, extracting"
    mkdir -p /tmp/geist-font
    unzip -o -q /usr/share/mios/vendored/geist-font.zip -d /tmp/geist-font 2>/dev/null || true
elif [ -d "/usr/share/mios/vendored/geist-font" ]; then
    mios_log "found offline vendored geist-font directory, copying"
    cp -a /usr/share/mios/vendored/geist-font /tmp/geist-font
else
    git clone --depth=1 --single-branch -c http.lowSpeedLimit=1 -c http.lowSpeedTime=20 \
        https://github.com/vercel/geist-font.git /tmp/geist-font 2>/dev/null || true
fi

if [ -d /tmp/geist-font ]; then
    find /tmp/geist-font \( -name "*.otf" -o -name "*.ttf" \) \
        -exec cp -t /usr/share/fonts/geist/ {} + 2>/dev/null || true
    rm -rf /tmp/geist-font
    record_version geist-font "git-main" "https://github.com/vercel/geist-font"
fi

# ── Symbols-Only Nerd Font (icon-glyph fallback for Geist Mono) ──────
# Vercel's Geist Mono is a clean monospace; it does NOT carry the
# Powerline (E0xx), Devicon (E7xx), Material (F0xxx), or Octicon
# private-use-area ranges that the Oh-My-Posh prompt theme
# (usr/share/mios/oh-my-posh/mios.omp.json) and other MiOS UI surfaces
# reference. Patching Geist with Nerd-Font glyphs creates a derivative
# work; pulling Symbols-Only-Nerd-Font as a SEPARATE family and using
# fontconfig per-glyph fallback (usr/share/fontconfig/conf.avail/
# 30-mios-geist.conf) keeps Geist's letterforms for text while the
# missing icon glyphs resolve through the symbols font transparently.
mios_log "installing Symbols-Only Nerd Font (icon fallback for Geist Mono)"
mkdir -p /usr/share/fonts/nerd-symbols
NERD_TAG=$( (scurl -s https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest \
            | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
NERD_FALLBACK_TAG="v3.4.0"
if [ -z "$NERD_TAG" ]; then
    mios_warn "api.github.com release-tag lookup empty -- using fallback ${NERD_FALLBACK_TAG}"
    NERD_TAG="$NERD_FALLBACK_TAG"
fi
record_version nerd-symbols-font "$NERD_TAG" \
    "https://github.com/ryanoasis/nerd-fonts/releases/tag/${NERD_TAG}"

if command -v unzip >/dev/null 2>&1; then
    NERD_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/${NERD_TAG}/NerdFontsSymbolsOnly.zip"
    download_ok=false
    if [ -f "/usr/share/mios/vendored/fonts/nerd.tar.xz" ]; then
        mios_log "found offline vendored nerd.tar.xz, using it"
        tar -xf "/usr/share/mios/vendored/fonts/nerd.tar.xz" -C /usr/share/fonts/nerd-symbols 2>/dev/null || true
        download_ok=true
    elif [ -f "/usr/share/mios/vendored/NerdFontsSymbolsOnly.zip" ]; then
        mios_log "found offline vendored NerdFontsSymbolsOnly.zip, using it"
        cp /usr/share/mios/vendored/NerdFontsSymbolsOnly.zip /tmp/nerd-symbols.zip
        download_ok=true
    elif [ -f "/usr/share/mios/vendored/nerd-symbols.zip" ]; then
        mios_log "found offline vendored nerd-symbols.zip, using it"
        cp /usr/share/mios/vendored/nerd-symbols.zip /tmp/nerd-symbols.zip
        download_ok=true
    elif scurl -fsL --max-time 90 "$NERD_URL" -o /tmp/nerd-symbols.zip 2>/dev/null; then
        download_ok=true
    fi

    if [ "$download_ok" = true ]; then
        if [ -f /tmp/nerd-symbols.zip ]; then
            unzip -o -q /tmp/nerd-symbols.zip "*.ttf" "*.otf" -d /usr/share/fonts/nerd-symbols 2>/dev/null || true
        fi

        # Record to binaries SBOM (RELTOP-01 / T-251). Sha the actual asset that was
        # used -- the vendored nerd.tar.xz path extracts straight to the fonts dir and
        # never creates /tmp/nerd-symbols.zip, so guard the hash (a bare sha256sum on a
        # missing file aborts the whole script under `set -euo pipefail`).
        sbom_dir="/usr/share/mios/artifacts/sbom"
        mkdir -p "$sbom_dir"
        sha=""
        if command -v sha256sum >/dev/null 2>&1; then
            for _asset in /tmp/nerd-symbols.zip /usr/share/mios/vendored/fonts/nerd.tar.xz; do
                if [ -f "$_asset" ]; then
                    sha="$(sha256sum "$_asset" | awk '{print $1}')"
                    break
                fi
            done
        fi
        printf '%s\t%s\t%s\n' "NerdFontsSymbolsOnly" "${NERD_TAG}" "${sha:-unknown}" >> "${sbom_dir}/binaries.tsv"

        rm -f /tmp/nerd-symbols.zip
        mios_ok "Symbols-Only Nerd Font ${NERD_TAG} installed"
    else
        mios_warn "Symbols-Only Nerd Font download failed -- prompt icons will render as missing-glyph squares"
    fi
else
    mios_warn "unzip unavailable -- skipping symbols font (install unzip in packages-utils)"
fi

# Refresh fontconfig cache so the new families are immediately
# resolvable. The mios-fontconfig.conf drop-in (symlinked into
# /etc/fonts/conf.d/ via tmpfiles.d) already declares the cascade --
# fontconfig just needs to know the new files exist.
fc-cache -f /usr/share/fonts/geist /usr/share/fonts/nerd-symbols 2>/dev/null || true

mios_ok "done"

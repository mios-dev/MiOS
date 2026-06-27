#!/usr/bin/env bash
# AI-hint: Build-time script that fetches and installs the OpenUI generative-UI bundle (JS/CSS) into /usr/share/mios/openui to ensure offline-first availability for the OWUI Tool.
# AI-related: /usr/share/mios/openui, /usr/share/mios/openui/., /usr/share/mios/vendored/, mios-vendor-openui
# automation/support/mios-vendor-openui.sh
#
# One-shot at IMAGE BUILD time: download the OpenUI generative-UI
# bundle (used by the OpenUI OWUI Tool) from jsDelivr and stash under
# /usr/share/mios/openui/. The Tool's iframe inlines these files at
# render time so no CDN fetch ever happens at runtime (Law 7
# OFFLINE-FIRST).
#
# Operator directive "NO!!!! FULL OFFLINE".
#
# Re-runnable: skips the download if files already present + non-zero.
# Network-best-effort: warns and exits 0 if jsDelivr is unreachable
# (the OWUI Tool falls back to a friendly "bundle missing" panel and
# the operator can re-run this script later).
set -euo pipefail

DEST=/usr/share/mios/openui
URL_BASE=https://cdn.jsdelivr.net/npm/@openuidev/browser-bundle/dist
FILES=(openui-bundle.min.js openui-styles.css)

install -d -m 0755 "$DEST"

for f in "${FILES[@]}"; do
    out="$DEST/$f"
    if [[ -s "$out" ]]; then
        echo "[mios-vendor-openui] keep existing $out ($(wc -c < "$out") bytes)"
        continue
    fi
    if [[ -f "/usr/share/mios/vendored/$f" ]]; then
        echo "[mios-vendor-openui] Found offline vendored file: /usr/share/mios/vendored/$f"
        cp "/usr/share/mios/vendored/$f" "$out"
        chmod 0644 "$out"
        continue
    fi
    if curl -sSL --max-time 60 -o "$out.tmp" "$URL_BASE/$f"; then
        if [[ -s "$out.tmp" ]]; then
            mv "$out.tmp" "$out"
            chmod 0644 "$out"
            echo "[mios-vendor-openui] downloaded $out ($(wc -c < "$out") bytes)"
        else
            rm -f "$out.tmp"
            echo "[mios-vendor-openui] WARN: downloaded zero-byte $f" >&2
        fi
    else
        rm -f "$out.tmp"
        echo "[mios-vendor-openui] WARN: $URL_BASE/$f unreachable -- OpenUI panel will be unavailable" >&2
    fi
done

# License notice (MIT, thesysdev/vishxrad)
cat > "$DEST/LICENSE.MIT" <<'EOF'
The OpenUI generative-UI bundle is licensed under the MIT License.
Source: https://github.com/thesysdev/openui (npm: @openuidev/browser-bundle)
The bundle file (openui-bundle.min.js) embeds @license React headers
internally; the full attribution is preserved in those header comments.
This MiOS image redistributes the unmodified bundle to satisfy
Law 7 OFFLINE-FIRST -- no runtime CDN fetches.
EOF
chmod 0644 "$DEST/LICENSE.MIT"

echo "[mios-vendor-openui] done. Bundle dir: $DEST"

#!/usr/bin/env bash
# /usr/libexec/mios/automation/35-xrdp-enhanced-session.sh
#
# Install + configure GNOME Remote Desktop in system/headless mode so
# the operator can connect from Windows via mstsc.exe and get a FULL
# GNOME desktop (rounded corners, libadwaita-consistent theming,
# Bibata cursor, single mutter compositor). Complements WSLg-per-window
# forwarding -- both launch paths remain available.
#
# Operator directive 2026-05-12:
#   "Full Enhanced Session is an alternate launch option installed at
#    irm|iex invoke and installation"
#
# Why GNOME Remote Desktop, not xrdp:
#   * xrdp's xorgxrdp Xorg backend SIGSEGVs on WSL2 ("X server failed
#     to start", display :10 unavailable)
#   * xrdp's Xvnc backend hits the same WSL2-can't-start-display issue
#   * GNOME Remote Desktop in --system mode uses gdm + per-user
#     headless gnome-session over a virtual fb provided by mutter
#     itself. No Xorg-on-WSL2 chicken-and-egg.
#
# Why port 13389 (not 3389):
#   Windows blocks RDP via loopback on 3389 with error 0x708
#   "console session in progress" -- bypassed by an alternate port.
#
# Why dual-stack via mios-route:
#   wslrelay's localhost forwarding only proxies IPv6 (::1) when the
#   server binds to `*:` without an explicit family. grdctl --system
#   set-port + binding via mutter's RDP server picks dual-stack
#   (we verified `LISTEN *:13389` shows up after gdm.service is up).
#
# Idempotent. Safe to re-run.
set -euo pipefail

_log() { printf '[grd-enhanced] %s\n' "$*" >&2; }

# ─── mios.toml resolver ──────────────────────────────────────────────
_mios_toml_value() {
    local section="$1" key="$2" def_val="$3"
    local toml
    for toml in "${HOME:-/var/home/mios}/.config/mios/mios.toml" /etc/mios/mios.toml /usr/share/mios/mios.toml; do
        [ -r "$toml" ] || continue
        local v
        v=$(awk -v want_section="$section" -v want_key="$key" '
            /^\[/ {
                line = $0
                sub(/[[:space:]]*#.*$/, "", line)
                in_s = (line == "[" want_section "]") ? 1 : 0
                next
            }
            in_s && /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ {
                line = $0
                sub(/[[:space:]]*#.*$/, "", line)
                eq = index(line, "=")
                if (eq == 0) next
                k = substr(line, 1, eq - 1)
                v = substr(line, eq + 1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
                gsub(/^"|"$/, "", v)
                if (k == want_key) { print v; exit }
            }
        ' "$toml" 2>/dev/null)
        if [ -n "$v" ]; then printf '%s' "$v"; return; fi
    done
    printf '%s' "$def_val"
}

PORT="$(_mios_toml_value 'enhanced_session' 'port' '13389')"
USER_NAME="$(_mios_toml_value 'enhanced_session' 'user' "$(_mios_toml_value 'identity' 'username' 'mios')")"
PASSWORD="$(_mios_toml_value 'identity' 'default_password' 'mios')"
ENABLED="$(_mios_toml_value 'enhanced_session' 'enabled' 'true')"

if [ "$ENABLED" != "true" ]; then
    _log "enhanced_session.enabled=false -- skipping grd install"
    exit 0
fi

# ─── Install packages (dnf) ──────────────────────────────────────────
_log "installing gnome-remote-desktop + gdm + winpr-utils + freerdp"
sudo dnf install -y --skip-unavailable \
    gnome-remote-desktop \
    gdm \
    winpr-utils \
    freerdp \
    gnome-session \
    gnome-shell \
    mutter \
    pipewire \
    pipewire-pulseaudio \
    >/dev/null

# ─── Generate TLS cert as the gnome-remote-desktop user ─────────────
# winpr-makecert is FreeRDP's certificate utility -- writes a cert
# that mstsc.exe will accept (sefl-signed warning on first connect
# is fine; operator clicks "Yes" to trust the loopback cert).
CERT_DIR="/var/lib/gnome-remote-desktop"
if [ ! -f "$CERT_DIR/rdp-tls.crt" ] || [ ! -f "$CERT_DIR/rdp-tls.key" ]; then
    _log "generating TLS cert at $CERT_DIR/rdp-tls.{crt,key}"
    sudo -u gnome-remote-desktop winpr-makecert -silent -rdp \
        -n localhost \
        -path "$CERT_DIR" \
        rdp-tls 2>/dev/null
fi

# ─── Configure --system grd via grdctl ──────────────────────────────
_log "configuring grd --system: port=$PORT user=$USER_NAME tls=$CERT_DIR/rdp-tls.*"
sudo grdctl --system rdp set-tls-cert "$CERT_DIR/rdp-tls.crt"
sudo grdctl --system rdp set-tls-key  "$CERT_DIR/rdp-tls.key"
sudo grdctl --system rdp set-credentials "$USER_NAME" "$PASSWORD"
sudo grdctl --system rdp set-port "$PORT"
sudo grdctl --system rdp enable

# ─── Enable gdm + grd services ──────────────────────────────────────
# gdm.service is the prerequisite -- without it, the grd daemon
# initializes but never binds the RDP port (no session manager to
# hand the per-user gnome-session over to).
_log "enabling gdm.service + gnome-remote-desktop.service"
sudo systemctl daemon-reload
sudo systemctl enable --now gdm.service gnome-remote-desktop.service

# Wait briefly for grd to actually bind the port
sleep 4

# ─── Verify ──────────────────────────────────────────────────────────
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    _log "gnome-remote-desktop listening on *:$PORT  (connect via mstsc /v:localhost:$PORT)"
else
    _log "WARN: grd NOT listening on :$PORT yet -- check 'journalctl -u gnome-remote-desktop.service'"
    sudo journalctl -u gnome-remote-desktop.service --no-pager 2>&1 | tail -5 | sed 's/^/[grd-enhanced]   /'
fi

_log "done. Enhanced Session ready. User=$USER_NAME  Password=[identity].default_password from mios.toml."

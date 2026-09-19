#!/bin/sh
# Start (or reuse) a session D-Bus + GNOME keyring so Antigravity's cached
# credentials survive across shells and tool calls in this container.
# The Antigravity CLI (agy) stores its OAuth credential in the OS keyring
# (Secret Service); without a running daemon a headless container re-asks for
# auth on every launch — which breaks multi-lane `agy -p` runs.
#
# Source it (safe to source repeatedly):   . skills/dev-loop/scripts/env/agy-keyring.sh
# The exported environment is persisted to $HOME/.config/agy-cloud/keyring.env
# so later shells reuse the same daemon instead of starting another.
#
# Trade-off, stated plainly: the default keyring is created UNENCRYPTED
# (lock-less plaintext file), so the cached credential is recoverable by anyone
# with access to this container. That is the accepted model for an ephemeral,
# single-user cloud session; do NOT copy this pattern to a shared or
# persistent host.

AGY_CLOUD_DIR="${AGY_CLOUD_DIR:-$HOME/.config/agy-cloud}"
AGY_KEYRING_ENV="$AGY_CLOUD_DIR/keyring.env"
mkdir -p "$AGY_CLOUD_DIR"

# The daemon is alive only if the bus socket exists AND something on that bus
# owns org.freedesktop.secrets (process-name checks lie: the kernel truncates
# comm to "gnome-keyring-d", and a daemon can be up with no secrets service).
agy_keyring_alive() {
    [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || return 1
    _sock="${DBUS_SESSION_BUS_ADDRESS#unix:path=}"
    [ "$_sock" != "$DBUS_SESSION_BUS_ADDRESS" ] || return 1   # only unix:path= addresses are checked
    [ -S "$_sock" ] || return 1
    if command -v dbus-send >/dev/null 2>&1; then
        dbus-send --session --print-reply --dest=org.freedesktop.DBus / \
            org.freedesktop.DBus.ListNames 2>/dev/null | grep -q org.freedesktop.secrets || return 1
    else
        pgrep -f gnome-keyring-daemon >/dev/null 2>&1 || return 1
    fi
    return 0
}

# Reuse a previous bootstrap if its daemon is still alive.
if [ -f "$AGY_KEYRING_ENV" ]; then
    # shellcheck disable=SC1090
    . "$AGY_KEYRING_ENV"
fi

if ! agy_keyring_alive; then
    if ! command -v dbus-daemon >/dev/null 2>&1 || ! command -v gnome-keyring-daemon >/dev/null 2>&1; then
        echo "agy-keyring: dbus / gnome-keyring not installed — run setup-antigravity.sh (this directory) first" >&2
        return 1 2>/dev/null || exit 1
    fi

    # A default collection must exist or every secret-tool/libsecret store fails
    # with "Object does not exist at path .../collection/login". An empty-stdin
    # --unlock does not create one headlessly, so pre-create an unencrypted
    # default keyring (standard headless-CI recipe).
    _krdir="$HOME/.local/share/keyrings"
    if [ ! -f "$_krdir/default" ]; then
        mkdir -p "$_krdir" && chmod 700 "$_krdir"
        cat > "$_krdir/Default_keyring.keyring" <<'EOF'
[keyring]
display-name=Default keyring
ctime=0
mtime=0
lock-on-idle=false
lock-after=false
EOF
        chmod 600 "$_krdir/Default_keyring.keyring"
        printf 'Default_keyring' > "$_krdir/default"
    fi

    # Replace any half-alive daemons from earlier attempts, then start fresh.
    # -x -f = exact full-command-line match only, so a shell that merely
    # mentions these strings (a test, an agent's command) is never killed.
    # `|| :` is load-bearing: pkill exits 1 when NOTHING matches, which is the
    # normal case on a fresh container, and under the caller's `set -e` that
    # killed agy-login.sh silently before it ever reached tmux.
    pkill -x -f "dbus-daemon --session --address=unix:path=$AGY_CLOUD_DIR/bus --fork" 2>/dev/null || :
    pkill -x -f "gnome-keyring-daemon --start --daemonize --components=secrets" 2>/dev/null || :
    pkill -x -f "gnome-keyring-daemon --unlock --replace --components=secrets" 2>/dev/null || :
    _bus="$AGY_CLOUD_DIR/bus"
    rm -f "$_bus"
    dbus-daemon --session --address="unix:path=$_bus" --fork >/dev/null 2>&1
    DBUS_SESSION_BUS_ADDRESS="unix:path=$_bus"
    export DBUS_SESSION_BUS_ADDRESS

    _out=$(gnome-keyring-daemon --start --daemonize --components=secrets 2>/dev/null) || true
    _ctrl=$(printf '%s\n' "$_out" | sed -n 's/^GNOME_KEYRING_CONTROL=//p' | head -1)
    if [ -n "$_ctrl" ]; then
        GNOME_KEYRING_CONTROL="$_ctrl"
        export GNOME_KEYRING_CONTROL
    fi

    {
        printf 'export DBUS_SESSION_BUS_ADDRESS="%s"\n' "$DBUS_SESSION_BUS_ADDRESS"
        [ -n "${GNOME_KEYRING_CONTROL:-}" ] && printf 'export GNOME_KEYRING_CONTROL="%s"\n' "$GNOME_KEYRING_CONTROL"
    } > "$AGY_KEYRING_ENV"
fi

# Positive control when the caller asks for it: prove the Secret Service can
# store AND read back a value (a keyring that silently stores nothing would
# let `agy` "succeed" while caching no credential — a check that cannot fail).
# Request it via env var — NOT a positional arg, because dash's `.` does not
# pass args to a sourced file, which silently skips the check under plain sh:
#   AGY_KEYRING_VERIFY=1 . skills/dev-loop/scripts/env/agy-keyring.sh
if { [ "${AGY_KEYRING_VERIFY:-0}" = 1 ] || [ "${1:-}" = "--verify" ]; } && command -v secret-tool >/dev/null 2>&1; then
    _nonce="agy-keyring-selftest-$$"
    if printf '%s' "$_nonce" | secret-tool store --label agy-keyring-selftest agy selftest 2>&1 \
       && [ "$(secret-tool lookup agy selftest 2>/dev/null)" = "$_nonce" ]; then
        secret-tool clear agy selftest 2>/dev/null || true
        echo "agy-keyring: OK (secret store/lookup round-trip passed)"
    else
        echo "agy-keyring: FAIL — Secret Service round-trip did not return the stored value" >&2
        return 1 2>/dev/null || exit 1
    fi
fi

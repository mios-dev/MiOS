#!/bin/bash
# Provision a container/VM with everything needed to run Google Antigravity's
# CLI (`agy`) as a dev-loop host and/or lane harness. Distro-aware: Fedora/RHEL
# family (dnf5 / dnf / microdnf) and Debian/Ubuntu family (apt-get).
#
#   1. OS packages: keyring stack (dbus, gnome-keyring, libsecret) + tmux, jq
#   2. The Antigravity CLI itself (official installer → ~/.local/bin/agy)
#   3. A running Secret Service keyring (env/agy-keyring.sh)
#   4. The dev-loop skill + /dev-loop workflow installed into Antigravity's
#      user-scope directories (~/.gemini/config/skills, ~/.gemini/antigravity/workflows)
#   5. PATH / keyring env persisted into $CLAUDE_ENV_FILE when set
#
# Idempotent and non-interactive: every step no-ops when already satisfied.
# Location-independent: works from the repo checkout or from an installed
# skill copy (paths are resolved relative to this file).
# Usage:  bash setup-antigravity.sh [--quiet]
set -euo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1
log() { [ "$QUIET" = 1 ] || echo "[antigravity-setup] $*"; }
warn() { echo "[antigravity-setup] WARN: $*" >&2; }

export DEBIAN_FRONTEND=noninteractive GIT_TERMINAL_PROMPT=0 PIP_NO_INPUT=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # …/scripts/env
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"                  # …/skills/dev-loop

# --- 1. OS packages -----------------------------------------------------------
# Detect the package manager once; map each missing binary to that family's
# package name. Fedora/RHEL first (the default devcontainer), then Debian/Ubuntu.
PM=""
for c in dnf5 dnf microdnf apt-get; do
    command -v "$c" >/dev/null 2>&1 && { PM="$c"; break; }
done

pkg_for() { # $1 = binary  → package name for $PM (empty = no mapping)
    case "$PM" in
        dnf5|dnf|microdnf)
            case "$1" in
                dbus-daemon) echo dbus-daemon;;        # also provides dbus-run-session
                dbus-send) echo dbus-tools;;
                gnome-keyring-daemon) echo gnome-keyring;;
                secret-tool) echo libsecret;;          # Fedora ships secret-tool in libsecret
                tmux) echo tmux;; jq) echo jq;; curl) echo curl;; python3) echo python3;;
            esac;;
        apt-get)
            case "$1" in
                dbus-daemon|dbus-send) echo dbus;;     # metapackage pulls daemon + tools
                gnome-keyring-daemon) echo gnome-keyring;;
                secret-tool) echo libsecret-tools;;
                tmux) echo tmux;; jq) echo jq;; curl) echo curl;; python3) echo python3;;
            esac;;
    esac
}

pkgs=""
for b in dbus-daemon dbus-send gnome-keyring-daemon secret-tool tmux jq curl python3; do
    command -v "$b" >/dev/null 2>&1 && continue
    p="$(pkg_for "$b")"
    [ -n "$p" ] && case " $pkgs " in *" $p "*) ;; *) pkgs="$pkgs $p";; esac
done
if [ -n "$pkgs" ]; then
    if [ -z "$PM" ]; then
        warn "no supported package manager (dnf5/dnf/microdnf/apt-get); missing:$pkgs"
    else
        SUDO=""
        [ "$(id -u)" = 0 ] || SUDO="sudo -n"
        log "installing via $PM:$pkgs"
        # shellcheck disable=SC2086
        case "$PM" in
            apt-get) { $SUDO apt-get update -qq || warn "apt-get update failed; trying existing indexes"; } \
                     && $SUDO apt-get install -y -qq $pkgs || warn "package install failed:$pkgs" ;;
            dnf5|dnf) $SUDO "$PM" -y -q install $pkgs || warn "package install failed:$pkgs" ;;
            microdnf) $SUDO microdnf -y install $pkgs || warn "package install failed:$pkgs" ;;
        esac
    fi
fi
# The keyring stack is load-bearing (auth persistence); say so if still absent.
for b in dbus-daemon gnome-keyring-daemon secret-tool; do
    command -v "$b" >/dev/null 2>&1 || warn "$b still missing — agy will re-ask for authentication on every launch"
done

# --- 2. Antigravity CLI (agy) -------------------------------------------------
export PATH="$HOME/.local/bin:$PATH"
if ! command -v agy >/dev/null 2>&1; then
    log "installing the Antigravity CLI from antigravity.google (→ ~/.local/bin/agy)"
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT
    # Download-then-run (never pipe-to-shell) so a truncated transfer fails loudly.
    curl -fsSL --retry 4 --retry-delay 2 https://antigravity.google/cli/install.sh -o "$tmpdir/install.sh"
    [ -s "$tmpdir/install.sh" ] || { echo "[antigravity-setup] ERROR: downloaded installer is empty" >&2; exit 1; }
    bash "$tmpdir/install.sh"
fi
command -v agy >/dev/null 2>&1 || { echo "[antigravity-setup] ERROR: agy still not on PATH after install" >&2; exit 1; }
AGY_VERSION="$(agy --version 2>/dev/null | head -1 || echo 'installed (version query failed)')"
log "agy: $AGY_VERSION"

# --- 3. keyring bootstrap ------------------------------------------------------
# shellcheck source=agy-keyring.sh
if . "$SCRIPT_DIR/agy-keyring.sh"; then
    log "keyring: Secret Service running (env cached in ~/.config/agy-cloud/keyring.env)"
else
    warn "keyring bootstrap failed — authentication will not persist across launches"
fi

# --- 4. dev-loop skill + /dev-loop workflow into Antigravity (user scope) ------
if [ -f "$HOME/.gemini/config/skills/dev-loop/SKILL.md" ]; then
    log "dev-loop skill already installed for Antigravity (user scope)"
elif sh "$SKILL_DIR/scripts/install.sh" --harness antigravity --user >/dev/null 2>&1; then
    log "dev-loop skill installed for Antigravity (user scope)"
else
    warn "dev-loop skill install for Antigravity reported errors; run it manually: sh $SKILL_DIR/scripts/install.sh --harness antigravity --user"
fi

# --- 4b. headless permission grants -------------------------------------------
# Headless agy cannot prompt, so it AUTO-DENIES any tool without a grant and still
# reports status SUCCESS with an empty response -- a lane that did nothing looks like a
# lane that passed. Grants are therefore part of provisioning, not an operator extra.
#
# Grammar (measured against agy 1.2.6, and nothing like Claude Code's `Bash(git:*)`):
#   * valid actions are read_file, write_file and command -- ANY other action name
#     (edit_file, list_dir, grep_search, run_command, invoke_subagent, ...) is DISCARDED
#     with only a log line, so a careful-looking allowlist can grant nothing at all;
#   * read_file/write_file take a target and do NOT glob over paths: `read_file(/repo/**)`
#     and `read_file(/repo/*)` are accepted and match nothing. Only an exact path or the
#     universal `(*)` works. GrepSearch resolves to read_file, so searching needs it too;
#   * command() prefix-matches the binary, so the shell stays scoped to this list --
#     which is what makes this narrower than --dangerously-skip-permissions.
AGY_SETTINGS="$HOME/.gemini/antigravity-cli/settings.json"
if [ -n "${MIOS_AGY_NO_GRANTS:-}" ]; then
    log "skipping permission grants (MIOS_AGY_NO_GRANTS set)"
elif command -v python3 >/dev/null 2>&1; then
    mkdir -p "$(dirname "$AGY_SETTINGS")"
    AGY_SETTINGS="$AGY_SETTINGS" python3 - <<'PY' && log "headless grants written to ~/.gemini/antigravity-cli/settings.json"
import json, os, pathlib
p = pathlib.Path(os.environ["AGY_SETTINGS"])
try:
    cfg = json.loads(p.read_text()) if p.is_file() else {}
except (json.JSONDecodeError, OSError):
    cfg = {}
if not isinstance(cfg, dict):
    cfg = {}
want = ["read_file(*)", "write_file(*)"] + [f"command({c})" for c in (
    "sh", "bash", "python3", "git", "cat", "grep", "head", "tail", "ls", "find",
    "wc", "sed", "awk", "mkdir", "cp", "mv", "printf", "echo", "jq", "cd")]
allow = cfg.setdefault("permissions", {}).setdefault("allow", [])
for rule in want:
    if rule not in allow:
        allow.append(rule)
p.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"[antigravity-setup] {len(want)} grant(s) ensured, {len(allow)} total")
PY
else
    warn "python3 missing -- cannot write permission grants; headless lanes will be auto-denied"
fi

# --- 5. persist session environment ---------------------------------------------
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    grep -qs 'agy-cloud/keyring.env' "$CLAUDE_ENV_FILE" 2>/dev/null || {
        echo 'export PATH="$HOME/.local/bin:$PATH"'
        echo '[ -f "$HOME/.config/agy-cloud/keyring.env" ] && . "$HOME/.config/agy-cloud/keyring.env"'
    } >> "$CLAUDE_ENV_FILE"
fi

# --- status ---------------------------------------------------------------------
if [ "$QUIET" = 1 ]; then
    echo "antigravity: $AGY_VERSION — if this container has not been authenticated yet, run: bash $SCRIPT_DIR/agy-login.sh (one-time Google sign-in)"
else
    log "done. Next (one-time per container): bash $SCRIPT_DIR/agy-login.sh"
    log "then verify with:                    bash $SCRIPT_DIR/agy-doctor.sh --probe"
fi

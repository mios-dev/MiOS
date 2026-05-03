# /etc/profile.d/mios-env.sh -- 'MiOS' login-shell environment resolver.
#
# Sourced from /etc/profile by every interactive login shell. Walks the
# documented five-layer overlay (INDEX.md sec 4) and exports the resolved
# MIOS_* variables so every agent and CLI sees the same values regardless
# of which shell or terminal launched them.
#
# Resolution order (later layers override earlier values):
#   1. /usr/share/mios/env.defaults    vendor defaults (lowest)
#   2. /etc/mios/env.d/*.env           admin/distro drop-ins (alphabetical)
#   3. /etc/mios/install.env           host bootstrap-written identity
#   4. ~/.env.mios                     legacy per-user (deprecated)
#   5. ~/.config/mios/env              per-user override (highest)
#
# Architectural Law 5 (UNIFIED-AI-REDIRECTS): MIOS_AI_ENDPOINT,
# MIOS_AI_MODEL, and MIOS_AI_KEY are exported here so every OpenAI-API
# client on the system resolves the same canonical surface at
# http://localhost:8080/v1.
#
# Safe to source in non-bash POSIX shells; uses only POSIX builtins.

# Bail out early on non-interactive non-login shells -- this file should
# not perturb cron jobs or systemd-spawned children.
case "$-" in
    *i*) ;;
    *)
        # Still export AI endpoint for non-interactive scripts; just skip
        # the chatty layer-walk and per-user reads.
        if [ -r /usr/share/mios/env.defaults ]; then
            # shellcheck disable=SC1091
            . /usr/share/mios/env.defaults
            export MIOS_AI_ENDPOINT MIOS_AI_MODEL MIOS_AI_KEY
        fi
        return 0 2>/dev/null || exit 0
        ;;
esac

_mios_source_if_readable() {
    [ -r "$1" ] || return 0
    # shellcheck disable=SC1090
    . "$1"
}

# Layer 1: vendor defaults (always present on a 'MiOS' system).
_mios_source_if_readable /usr/share/mios/env.defaults

# Layer 2: admin / distro drop-ins (alphabetical, env-style).
if [ -d /etc/mios/env.d ]; then
    for _f in /etc/mios/env.d/*.env; do
        _mios_source_if_readable "$_f"
    done
    unset _f
fi

# Layer 3: host install.env -- bootstrap writes identity here.
_mios_source_if_readable /etc/mios/install.env

# Layer 4: legacy per-user env file (deprecated; kept for migration).
_mios_source_if_readable "${HOME}/.env.mios"

# Layer 5: canonical per-user env override.
_mios_source_if_readable "${HOME}/.config/mios/env"

# Export the OpenAI-API surface required by every Law-5-compliant agent.
export MIOS_AI_ENDPOINT="${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}"
export MIOS_AI_MODEL="${MIOS_AI_MODEL:-qwen2.5-coder:7b}"
export MIOS_AI_EMBED_MODEL="${MIOS_AI_EMBED_MODEL:-nomic-embed-text}"
export MIOS_AI_KEY="${MIOS_AI_KEY:-}"

# Identity surface (consumed by 'mios' CLI, ai-bootstrap, postcheck).
export MIOS_USER="${MIOS_USER:-${MIOS_DEFAULT_USER:-mios}}"
export MIOS_HOSTNAME="${MIOS_HOSTNAME:-${MIOS_DEFAULT_HOST:-mios}}"
export MIOS_VERSION="${MIOS_VERSION:-}"

# Runtime path surface (used by tools/lib/userenv.sh and the 'mios' CLI).
export MIOS_SHARE_DIR="${MIOS_SHARE_DIR:-/usr/share/mios}"
export MIOS_AI_DIR="${MIOS_AI_DIR:-/usr/share/mios/ai}"
export MIOS_AI_SCRATCH_DIR="${MIOS_AI_SCRATCH_DIR:-/var/lib/mios/ai/scratch}"
export MIOS_AI_MEMORY_DIR="${MIOS_AI_MEMORY_DIR:-/var/lib/mios/ai/memory}"

unset -f _mios_source_if_readable

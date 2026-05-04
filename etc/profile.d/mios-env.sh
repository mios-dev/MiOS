# /etc/profile.d/mios-env.sh -- 'MiOS' login-shell environment resolver.
#
# Sourced from /etc/profile by every interactive login shell. Walks the
# documented five-layer overlay (INDEX.md sec 4) and exports the resolved
# MIOS_* variables so every agent and CLI sees the same values regardless
# of which shell or terminal launched them.
#
# Resolution order (later layers override earlier values, so this list
# runs from LOWEST precedence to HIGHEST):
#   1. /usr/share/mios/env.defaults    vendor defaults (lowest)
#   2. ~/.env.mios                     legacy per-user (deprecated;
#                                      sourced before admin/host so a
#                                      stale legacy value cannot
#                                      override a fresher install.env
#                                      or env.d/*.env entry)
#   3. /etc/mios/env.d/*.env           admin/distro drop-ins (alphabetical)
#   4. /etc/mios/install.env           host bootstrap-written identity
#   5. ~/.config/mios/env              canonical per-user override (highest)
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

# Layer 1 (lowest): vendor defaults (always present on a 'MiOS' system).
_mios_source_if_readable /usr/share/mios/env.defaults

# Layer 2: legacy per-user env file (deprecated; sourced before
# admin/host so a stale ~/.env.mios cannot override fresher data).
_mios_source_if_readable "${HOME}/.env.mios"

# Layer 3: admin / distro drop-ins (alphabetical, env-style).
if [ -d /etc/mios/env.d ]; then
    for _f in /etc/mios/env.d/*.env; do
        _mios_source_if_readable "$_f"
    done
    unset _f
fi

# Layer 4: host install.env -- bootstrap writes identity here.
_mios_source_if_readable /etc/mios/install.env

# Layer 5 (highest): canonical per-user env override.
_mios_source_if_readable "${HOME}/.config/mios/env"

# Export the OpenAI-API surface required by every Law-5-compliant agent.
export MIOS_AI_ENDPOINT="${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}"
export MIOS_AI_MODEL="${MIOS_AI_MODEL:-qwen2.5-coder:7b}"
export MIOS_AI_EMBED_MODEL="${MIOS_AI_EMBED_MODEL:-nomic-embed-text}"
export MIOS_AI_KEY="${MIOS_AI_KEY:-}"

# Ollama-specific bind. /usr/bin/ollama (upstream CLI) reads OLLAMA_HOST
# to find the API server. The MiOS Ollama Quadlet
# (usr/share/containers/systemd/ollama.container) publishes 0.0.0.0:11434
# on the host, so any host-side shell -- including Ptyxis flatpak's
# default `flatpak-spawn --host bash` session -- talks to it via this
# env. Set explicitly here so `ollama list` / `ollama run <model>` work
# without arguments out of the box. Architectural Law 5 still has the
# canonical OpenAI surface at MIOS_AI_ENDPOINT (LocalAI on :8080);
# Ollama's OpenAI-compatible endpoint at localhost:11434/v1 is reached
# via the mios-ollama wrapper or by overriding MIOS_AI_ENDPOINT.
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

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

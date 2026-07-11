#!/usr/bin/bash
# AI-hint: greenboot required check that verifies the core MiOS AI plane (agent-pipe, llm-light, pgvector) answered after boot; a non-zero exit triggers bootc rollback. Service ports are sourced from the SSOT bridge (/etc/mios/install.env) and only ENABLED services are probed, so it degrades open instead of false-failing.
# AI-related: mios-greenboot, mios-agent-pipe.service, mios-llm-light.service, mios-pgvector.service, /etc/mios/install.env, mios-sync-env
# 'MiOS' greenboot -- required AI-plane readiness check.
#
# Verifies the CORE local AI services came up after a boot:
#   * mios-agent-pipe  -- front-door orchestrator (HTTP GET /v1/models, keyless)
#   * mios-llm-light   -- primary inference + embeddings lane (TCP reachable)
#   * mios-pgvector    -- unified agent datastore (TCP reachable)
#
# A non-zero exit makes greenboot retry and, after GREENBOOT_MAX_BOOT_ATTEMPTS
# consecutive failures, roll the deployment back -- so this MUST fail ONLY on a
# genuine AI-plane outage. Three safeguards keep it rollback-safe:
#   1. enabled-guard: a service is probed only when `systemctl is-enabled` says
#      it is wanted on this role, so a host that gates a lane off never trips it.
#   2. SSOT ports: every port is read from /etc/mios/install.env (MIOS_PORT_*,
#      derived from mios.toml [ports] by mios-sync-env). A port that did not
#      resolve is SKIPPED, never guessed -- no hardcoded literals, no false fail.
#   3. bounded retry: each probe waits up to TIMEOUT seconds before failing.
set -euo pipefail

TIMEOUT=60          # max seconds to wait per service before declaring it down
POLL=3              # seconds between probe attempts
PROBE_TIMEOUT=3     # per-attempt connection timeout
HOST=127.0.0.1      # core AI services bind loopback (host-net / localhost)
ENV_FILE=/etc/mios/install.env

log()  { echo "[mios-greenboot] $*"; }
fail() { echo "[mios-greenboot] $*" >&2; }

# Ports come from the SSOT bridge. Tolerate its absence OR a parse hiccup
# (degrade-open: without resolved ports we SKIP probes rather than guess a
# literal or abort -- a config-bridge glitch must never roll the OS back).
# install.env is plain KEY="value"; mirror the firstboot scripts' source idiom.
if [[ -r "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    # Guard set -u: a value with shell-metachars must not abort under set -u.
    _mios_had_u=0; case "$-" in *u*) _mios_had_u=1;; esac
    set +u; set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
    [ "$_mios_had_u" = 1 ] && set -u
fi

# TCP reachability via bash /dev/tcp -- no nc/curl dependency. `timeout` bounds
# the connect (a bare /dev/tcp open otherwise uses the multi-minute kernel
# default). Returns 0 when the listener accepts a connection.
_tcp_up() {
    local host="$1" port="$2"
    timeout "$PROBE_TIMEOUT" bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null
}

# HTTP liveness: "up" iff the service returns an HTTP status < 500 (the same
# convention the agent-pipe applies to its own liveness probes -- a 4xx still
# proves the listener is serving). Connection-refused / timeout -> curl emits
# 000 -> down. Falls back to a TCP connect when curl is unavailable.
_http_up() {
    local host="$1" port="$2" path="$3" code
    if ! command -v curl >/dev/null 2>&1; then
        if _tcp_up "$host" "$port"; then return 0; else return 1; fi
    fi
    code="$(curl -sS -o /dev/null -w '%{http_code}' \
        --max-time "$PROBE_TIMEOUT" "http://${host}:${port}${path}" 2>/dev/null || true)"
    case "$code" in
        [1-4][0-9][0-9]) return 0 ;;   # 100-499: listener served a response -> up
        *)               return 1 ;;   # 000 (refused/timeout) or 5xx -> down
    esac
}

# check_service <unit> <port> <kind> [http-path]
#   kind=http : HTTP liveness probe at <http-path>
#   kind=tcp  : TCP connect probe
# Returns 0 (skip) when the unit is not enabled here or its SSOT port did not
# resolve. Returns 0 (pass) when the probe answers within TIMEOUT. Returns 1
# only when an enabled service with a known port never answers.
check_service() {
    local unit="$1" port="$2" kind="$3" path="${4:-}" deadline probe_desc

    if ! systemctl is-enabled --quiet "$unit" 2>/dev/null; then
        log "${unit} not enabled on this role -- skipping."
        return 0
    fi
    if [[ -z "$port" ]]; then
        log "${unit}: port unresolved from ${ENV_FILE} -- skipping (no hardcoded fallback)."
        return 0
    fi

    probe_desc="${kind} ${HOST}:${port}${path}"
    log "${unit}: probing ${probe_desc} (up to ${TIMEOUT}s)..."
    deadline=$(( $(date +%s) + TIMEOUT ))
    while true; do
        if [[ "$kind" == "http" ]]; then
            if _http_up "$HOST" "$port" "$path"; then
                log "${unit}: healthy (${probe_desc})."
                return 0
            fi
        else
            if _tcp_up "$HOST" "$port"; then
                log "${unit}: healthy (${probe_desc})."
                return 0
            fi
        fi
        if [[ $(date +%s) -ge $deadline ]]; then
            fail "FAIL: ${unit} did not answer ${probe_desc} within ${TIMEOUT}s."
            return 1
        fi
        sleep "$POLL"
    done
}

rc=0
# agent-pipe front door: keyless GET /v1/models (in the pipe's _AUTH_OPEN_PATHS).
check_service mios-agent-pipe.service "${MIOS_PORT_AGENT_PIPE:-}" http /v1/models || rc=1
# primary inference + embeddings lane: TCP reachability of the llama-swap proxy.
check_service mios-llm-light.service  "${MIOS_PORT_LLM_LIGHT:-}"  tcp || rc=1
# unified agent datastore: TCP reachability of PostgreSQL + pgvector.
check_service mios-pgvector.service   "${MIOS_PORT_PGVECTOR:-}"   tcp || rc=1

if [[ "$rc" -eq 0 ]]; then
    log "AI plane healthy (all enabled core services answered)."
fi
exit "$rc"

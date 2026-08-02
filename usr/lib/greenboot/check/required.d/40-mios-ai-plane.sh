#!/usr/bin/bash
# AI-hint: greenboot required check that verifies the core MiOS AI plane (agent-pipe, llm-light, pgvector) answered after boot; a non-zero exit triggers bootc rollback. Service ports are sourced from the SSOT bridge (/etc/mios/install.env) and only ENABLED services are probed, so it degrades open instead of false-failing.
# AI-related: mios-greenboot, mios-agent-pipe.service, mios-llm-light.service, mios-pgvector.service, /etc/mios/install.env, mios-sync-env
set -euo pipefail

TIMEOUT=60          # max seconds to wait per service before declaring it down
POLL=3              # seconds between probe attempts
PROBE_TIMEOUT=3     # per-attempt connection timeout
HOST=127.0.0.1      # core AI services bind loopback (host-net / localhost)
ENV_FILE=/etc/mios/install.env

log()  { echo "[mios-greenboot] $*"; }
fail() { echo "[mios-greenboot] $*" >&2; }

if [[ -r "$ENV_FILE" ]]; then
    _mios_had_u=0; case "$-" in *u*) _mios_had_u=1;; esac
    set +u; set -a; source "$ENV_FILE" 2>/dev/null || true; set +a
    [ "$_mios_had_u" = 1 ] && set -u
fi

_tcp_up() {
    local host="$1" port="$2"
    timeout "$PROBE_TIMEOUT" bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null
}

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

check_service() {
    local unit="$1" port="$2" kind="$3" path="${4:-}" deadline probe_desc

    if ! systemctl is-enabled --quiet "$unit" 2>/dev/null; then
        log "${unit} not enabled on this role"
        return 0
    fi
    if [[ -z "$port" ]]; then
        log "${unit}: port unresolved from ${ENV_FILE}"
        return 0
    fi

    probe_desc="${kind} ${HOST}:${port}${path}"
    log "${unit}: probing ${probe_desc}"
    deadline=$(( $(date +%s) + TIMEOUT ))
    while true; do
        if [[ "$kind" == "http" ]]; then
            if _http_up "$HOST" "$port" "$path"; then
                log "${unit}: healthy"
                return 0
            fi
        else
            if _tcp_up "$HOST" "$port"; then
                log "${unit}: healthy"
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
check_service mios-agent-pipe.service "${MIOS_PORT_AGENT_PIPE:-}" http /v1/models || rc=1
check_service mios-llm-light.service  "${MIOS_PORT_LLM_LIGHT:-}"  tcp || rc=1
check_service mios-pgvector.service   "${MIOS_PORT_PGVECTOR:-}"   tcp || rc=1
check_service hermes.service          "${MIOS_PORT_HERMES:-}"     tcp || rc=1

if [[ "$rc" -eq 0 ]]; then
    log "AI plane healthy"
fi
exit "$rc"

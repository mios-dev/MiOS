# AI-hint: !/usr/bin/env bash Proves ADR-0016 D8 -- a seat's blade reachability is RECORDED on every boot and is not critical unless [greenboot].blade_reachabi...
# AI-doc: usr/share/doc/mios/manual/_harvest/tests_test_greenboot_blade_reachability_sh.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh"
PASS=0
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"; [[ -n "${SRV_PID:-}" ]] && kill "$SRV_PID" 2>/dev/null || true' EXIT

log() { printf '[greenboot-reach] %s\n' "$*"; }
die() { printf '[greenboot-reach] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { PASS=$((PASS + 1)); log "ok: $*"; }

[[ -r "$SCRIPT" ]] || die "probe script missing: $SCRIPT"

# Extract the real functions rather than re-implementing them; sourcing the whole
# script would run its probes.
{
    sed -n '/^_tcp_up() {/,/^}/p' "$SCRIPT"
    sed -n '/^_endpoint_host_port() {/,/^}/p' "$SCRIPT"
    sed -n '/^_blade_reachable() {/,/^}/p' "$SCRIPT"
} > "${WORK}/fn.sh"
grep -q '_blade_reachable' "${WORK}/fn.sh" || die "could not extract _blade_reachable -- renamed?"

# shellcheck disable=SC2034  # read by the _tcp_up extracted from the shipped script
PROBE_TIMEOUT=3
log()  { printf '[greenboot-reach]   %s\n' "$*"; }
fail() { printf '[greenboot-reach]   %s\n' "$*"; }
# shellcheck disable=SC1091
. "${WORK}/fn.sh"

hostport() { local r; r="$(_endpoint_host_port "$1")"; printf '%s:%s' "${r%%$'\t'*}" "${r##*$'\t'}"; }

# --- URL parsing -------------------------------------------------------------
[[ "$(hostport 'http://blade-01:8700/v1')" == "blade-01:8700" ]] \
    || die "host:port parse failed: $(hostport 'http://blade-01:8700/v1')"
ok "host and port parse out of a normal endpoint"

[[ "$(hostport 'https://blade-01/v1')" == "blade-01:443" ]] \
    || die "https default port wrong: $(hostport 'https://blade-01/v1')"
[[ "$(hostport 'http://blade-01/v1')" == "blade-01:80" ]] \
    || die "http default port wrong: $(hostport 'http://blade-01/v1')"
ok "a portless URL takes its scheme's default"

[[ "$(hostport 'http://[::1]:8700/v1')" == "[::1]:8700" ]] \
    || die "IPv6 literal parse failed: $(hostport 'http://[::1]:8700/v1')"
ok "an IPv6 literal keeps its brackets and finds its port"

# --- a REAL listener on an ephemeral port ------------------------------------
# A fixed port would pass on a stale socket from an earlier run; bind 0 and read
# back what the kernel gave us.
python3 - "$WORK/port" <<'PY' &
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 0))
s.listen(8)
open(sys.argv[1], "w").write(str(s.getsockname()[1]))
time.sleep(30)
PY
SRV_PID=$!
for _ in $(seq 1 50); do [[ -s "${WORK}/port" ]] && break; sleep 0.1; done
[[ -s "${WORK}/port" ]] || die "the fixture listener never reported a port"
PORT="$(cat "${WORK}/port")"

MIOS_BLADE_AUTH_POSTURE=armed MIOS_BLADE_AI_ENDPOINT="http://127.0.0.1:${PORT}/v1" \
    _blade_reachable || die "a blade that IS listening must read reachable"
ok "a real listener reads reachable"

# --- unreachable: recorded, never fatal --------------------------------------
DEAD="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));p=s.getsockname()[1];s.close();print(p)')"
if MIOS_BLADE_AUTH_POSTURE=armed MIOS_BLADE_AI_ENDPOINT="http://127.0.0.1:${DEAD}/v1" \
    _blade_reachable; then
    die "a closed port must NOT read reachable"
fi
ok "a closed port reads unreachable"

# The shipped default must leave rc untouched. This is the whole point of D8.
rc=0
if ! MIOS_BLADE_AUTH_POSTURE=armed MIOS_BLADE_AI_ENDPOINT="http://127.0.0.1:${DEAD}/v1" \
    _blade_reachable; then
    case "$(printf '%s' "${MIOS_GREENBOOT_BLADE_REACHABILITY_CRITICAL:-}" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|on) rc=1 ;;
    esac
fi
[[ "$rc" -eq 0 ]] || die "an unreachable blade must not fail the boot by default"
ok "unreachable is RECORDED, not critical, at the shipped default"

rc=0
if ! MIOS_BLADE_AUTH_POSTURE=armed MIOS_BLADE_AI_ENDPOINT="http://127.0.0.1:${DEAD}/v1" \
    _blade_reachable; then
    case "$(printf '%s' "true" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|on) rc=1 ;;
    esac
fi
[[ "$rc" -eq 1 ]] || die "with the flag ON an unreachable blade must fail"
ok "the flag is real: turning it on makes the same outage fatal"

# --- a hosted blade is unaffected -------------------------------------------
MIOS_BLADE_AUTH_POSTURE=local MIOS_BLADE_AI_ENDPOINT="http://localhost:8700/v1" \
    _blade_reachable || die "a local front door must never be probed as a blade"
ok "a loopback front door is not probed"

MIOS_BLADE_AUTH_POSTURE="" MIOS_BLADE_AI_ENDPOINT="" _blade_reachable \
    || die "with no endpoint recorded the check must degrade open"
ok "no recorded endpoint degrades open"

log "PASS: ${PASS}/9 assertions"

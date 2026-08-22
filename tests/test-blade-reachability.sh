#!/usr/bin/env bash
# AI-hint: Proves `mios blade status` answers the one question a MiOS-Mini seat has -- is my blade there? On a seat every offload target is REMOTE, and an unreachable blade otherwise looks like a broken model: the lane resolver returns its terminal lane even when the probe fails (by design, so a turn degrades rather than dead-ends), so all the operator sees is a transport error. Drives the real verb against a real /etc/mios overlay and a real listening socket -- no mocks: one target is up, one is not, and the nodes the overlay does not name stay local.
# AI-related: usr/libexec/mios/mios-blade, usr/lib/mios/blade.sh, usr/share/mios/mios.toml, usr/share/doc/mios/reference/mini-vs-hosted.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0

log() { printf '[blade-reachability] %s\n' "$*"; }
die() { printf '[blade-reachability] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { PASS=$((PASS + 1)); log "ok: $*"; }

command -v curl >/dev/null 2>&1 || { log "SKIP: curl absent"; exit 0; }
HOST="$(hostname)"
getent hosts "$HOST" >/dev/null 2>&1 || HOST="127.0.0.1"

FIXTURE="$(mktemp -d)"
SRV_PID=""
cleanup() { [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null || true; rm -rf "$FIXTURE"; }
trap cleanup EXIT

# A REAL socket on an EPHEMERAL port: a fixed port lets a stale listener from a
# previous run fake a pass, which is exactly what happened while writing this.
python3 - "${FIXTURE}/port" <<'SRV' &
import http.server, socketserver, sys


class Q(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("0.0.0.0", 0), Q)
with open(sys.argv[1], "w") as fh:
    fh.write(str(srv.server_address[1]))
srv.serve_forever()
SRV
SRV_PID=$!

PORT=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
    [ -s "${FIXTURE}/port" ] && PORT="$(cat "${FIXTURE}/port")" && break
    sleep 0.3
done
[ -n "$PORT" ] || { log "SKIP: the probe server never reported a port"; exit 0; }

for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -sS -o /dev/null --max-time 1 "http://${HOST}:${PORT}/" 2>/dev/null && break
    sleep 0.3
done
curl -sS -o /dev/null --max-time 2 "http://${HOST}:${PORT}/" 2>/dev/null \
    || die "bound port ${PORT} but could not reach it -- the probe is not proving anything"
# A port nothing is listening on. +1 from an ephemeral port is free in
# practice; the assertion below fails loudly if it ever is not.
DEAD=$((PORT + 1))
cat > "${FIXTURE}/mios.toml" <<EOF
[ai]
endpoint = "http://${HOST}:${PORT}/v1"

[search]
endpoint = "http://${HOST}:${DEAD}/"
EOF

run_status() {
    MIOS_USR_DIR="${ROOT}/usr/lib/mios" \
    MIOS_ETC_DIR="$FIXTURE" \
    MIOS_HOST_TOML="${FIXTURE}/mios.toml" \
    MIOS_USER_TOML=/dev/null \
    MIOS_BLADE_PROBE_TIMEOUT=2 \
    MIOS_PORT_CPU_NODE=8510 MIOS_PORT_LLM_LIGHT=8500 \
    MIOS_PORT_SGLANG=8530 MIOS_PORT_VLLM=8520 \
        bash "${ROOT}/usr/libexec/mios/mios-blade" status 2>&1
}

OUT="$(run_status)"

grep -q '^Offload targets:' <<<"$OUT" \
    || die "status does not report offload targets:
$OUT"
ok "status reports where this blade's services live"

grep -qE "^  ai +REMOTE +up " <<<"$OUT" \
    || die "the overlay's AI endpoint must read REMOTE and up:
$OUT"
ok "an offloaded target that answers reads REMOTE up"

grep -qE "^  search +REMOTE +UNREACHABLE " <<<"$OUT" \
    || die "an offloaded target that does NOT answer must read UNREACHABLE:
$OUT"
ok "an offloaded target that does not answer reads REMOTE UNREACHABLE"

grep -qE "^  node:local-sglang +local " <<<"$OUT" \
    || die "a target the overlay does not name must stay local:
$OUT"
ok "targets the overlay does not name stay local"

# The seat/blade tell: with NO overlay every target is local.
OUT_LOCAL="$(MIOS_USR_DIR="${ROOT}/usr/lib/mios" MIOS_ETC_DIR="$FIXTURE" \
    MIOS_HOST_TOML=/dev/null MIOS_USER_TOML=/dev/null MIOS_BLADE_PROBE_TIMEOUT=1 \
    MIOS_PORT_AGENT_PIPE=8700 MIOS_PORT_SEARXNG=8800 MIOS_PORT_CPU_NODE=8510 \
    MIOS_PORT_LLM_LIGHT=8500 MIOS_PORT_SGLANG=8530 MIOS_PORT_VLLM=8520 \
    bash "${ROOT}/usr/libexec/mios/mios-blade" status 2>&1)"
grep -q 'REMOTE' <<<"$OUT_LOCAL" \
    && die "with no overlay nothing should be REMOTE:
$OUT_LOCAL"
ok "with no overlay every target is local -- that is the seat/blade tell"

# An unresolved placeholder must be VISIBLE, never probed as a literal URL.
OUT_RAW="$(MIOS_USR_DIR="${ROOT}/usr/lib/mios" MIOS_ETC_DIR="$FIXTURE" \
    MIOS_HOST_TOML=/dev/null MIOS_USER_TOML=/dev/null MIOS_BLADE_PROBE_TIMEOUT=1 \
    bash "${ROOT}/usr/libexec/mios/mios-blade" status 2>&1)"
grep -q 'UNRESOLVED' <<<"$OUT_RAW" \
    || die "an unexpanded \${MIOS_PORT_*} must be reported UNRESOLVED, not probed:
$OUT_RAW"
ok "an unexpanded placeholder is reported, not silently probed"

log "PASS: ${PASS}/6 assertions"

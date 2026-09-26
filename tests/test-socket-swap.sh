#!/usr/bin/env bash
# AI-hint: Integration test suite for zero-downtime socket handoff and daemon swapper (T-542, AGY-2140).
# AI-doc: usr/share/doc/mios/manual/ch87-socket-activation-handoff.md
set -euo pipefail

ROOT="${MIOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SWAP_BIN="${ROOT}/usr/libexec/mios/mios-socket-swap"
SOCKET_UNIT="${ROOT}/usr/lib/systemd/system/mios-agent-pipe.socket"

echo "=== MiOS Socket Handoff Swapper Test Suite (T-542, AGY-2140) ==="

# Test 1: CLI and help verification
echo "--- Test 1: CLI and help verification ---"
python3 "${SWAP_BIN}" --help >/dev/null
python3 "${SWAP_BIN}" swap --help >/dev/null
python3 "${SWAP_BIN}" status --help >/dev/null
echo "  [PASS] CLI help flags verified"

# Test 2: File descriptor passing and listener handoff (positive control)
echo "--- Test 2: File descriptor passing and listener handoff ---"
MOCK_DIR="$(mktemp -d -t mios-sock-test-XXXXXX)"
# A mock swap leaves its worker running and holding this script's stdout, so a
# caller capturing the output (run-suites.sh) would wait forever: stop it here.
cleanup() {
    pid="$(python3 "${SWAP_BIN}" --mock --state-dir "${MOCK_DIR}" status --json 2>/dev/null \
           | python3 -c 'import json,sys; print(json.load(sys.stdin).get("active_pid") or "")' 2>/dev/null || true)"
    [ -n "${pid}" ] && kill "${pid}" 2>/dev/null || true
    rm -rf "${MOCK_DIR}"
}
trap cleanup EXIT

python3 -c "
import socket, array, os
s1, s2 = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('127.0.0.1', 0))
listener.listen(5)
port = listener.getsockname()[1]

# Send FD
s1.sendmsg([b'PASS_FD'], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [listener.fileno()]))])

# Recv FD
fds = array.array('i')
cmsg_space = socket.CMSG_LEN(1 * fds.itemsize)
msg, ancdata, _, _ = s2.recvmsg(1024, cmsg_space)
for cmsg_level, cmsg_type, cmsg_data in ancdata:
    if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
        fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        recv_listener = socket.fromfd(fds[0], socket.AF_INET, socket.SOCK_STREAM)
        assert recv_listener.getsockname()[1] == port, 'Port mismatch on inherited FD'
print('  [PASS] SCM_RIGHTS FD transfer confirmed')
"

# Test 3: Systemd socket unit validation
echo "--- Test 3: Systemd socket unit validation ---"
[ -f "${SOCKET_UNIT}" ] || { echo "ERROR: ${SOCKET_UNIT} missing"; exit 1; }
grep -q "ListenStream=8642" "${SOCKET_UNIT}"
grep -q "ListenStream=/run/mios/agent-pipe.sock" "${SOCKET_UNIT}"
if command -v systemd-analyze >/dev/null 2>&1; then
    systemd-analyze verify "${SOCKET_UNIT}" 2>&1 | grep -v "Unit.*is not executable" || true
fi
echo "  [PASS] Socket unit directives validated"

# Test 4: Mock end-to-end socket swap lifecycle (--mock)
echo "--- Test 4: Mock end-to-end socket swap lifecycle ---"
python3 "${SWAP_BIN}" --mock --state-dir "${MOCK_DIR}" swap --service agent-pipe --timeout 5.0
STATUS_OUT="$(python3 "${SWAP_BIN}" --mock --state-dir "${MOCK_DIR}" status --json)"
echo "${STATUS_OUT}" | grep -q '"transitions_count": 1'
echo "  [PASS] Mock socket swap executed successfully with recorded transition"

# Test 5: Negative control - candidate startup crash triggers abort and rollback
echo "--- Test 5: Negative control - candidate startup crash triggers abort ---"
set +e
python3 "${SWAP_BIN}" --mock --state-dir "${MOCK_DIR}" swap --service agent-pipe --candidate "false" --timeout 2.0 >/dev/null 2>&1
CRASH_EC=$?
set -e
[ "${CRASH_EC}" -ne 0 ] || { echo "ERROR: Expected non-zero exit on crashed candidate"; exit 1; }
echo "  [PASS] Candidate startup failure safely aborted swap"

echo "====================================================================="
echo "Socket Swap Test Results: ALL PASSED"
echo "====================================================================="
exit 0

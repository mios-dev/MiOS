#!/usr/bin/env bash
set -euo pipefail
# 'MiOS' v0.2.0 -- Ephemeral QEMU boot test
# Usage: bcvk-wrapper.sh <qcow2-path> [serial-log-path]
#
# Boots a QCOW2 image in headless QEMU with KVM, captures serial console,
# waits for systemd to reach a login target, then exits.
# Returns 0 on success, non-zero on timeout or boot failure.

QCOW="${1:-}"
SERIAL_LOG="${2:-/tmp/mios-serial.log}"
TIMEOUT_SECS=240
POLL_INTERVAL=3

if [[ -z "$QCOW" ]]; then
    echo "Usage: $0 <qcow2-path> [serial-log-path]"
    exit 2
fi

if [[ ! -f "$QCOW" ]]; then
    echo "ERROR: QCOW2 not found: $QCOW"
    exit 3
fi

: > "$SERIAL_LOG"

echo "[bcvk] Booting $QCOW (timeout: ${TIMEOUT_SECS}s)"

QEMU_ARGS=(
    qemu-system-x86_64
    -m 16384
    -smp 8
    -cpu host
    -enable-kvm
    -drive "file=$QCOW,if=virtio,cache=none,format=qcow2"
    -nic "user,model=virtio"
    -nographic
    -serial "file:$SERIAL_LOG"
    -no-reboot
    -display none
)

"${QEMU_ARGS[@]}" &
QEMU_PID=$!

cleanup() { kill "$QEMU_PID" 2>/dev/null; wait "$QEMU_PID" 2>/dev/null; }
trap cleanup EXIT

ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT_SECS ]]; do
    if grep -qE "(Reached target (Graphical|Multi-User)|login:)" "$SERIAL_LOG" 2>/dev/null; then
        echo "[bcvk] Boot successful (${ELAPSED}s)"
        exit 0
    fi
    if grep -qi "kernel panic" "$SERIAL_LOG" 2>/dev/null; then
        echo "[bcvk] KERNEL PANIC detected"
        tail -50 "$SERIAL_LOG"
        exit 5
    fi
    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo "[bcvk] TIMEOUT after ${TIMEOUT_SECS}s -- boot did not reach target"
echo "[bcvk] Last 100 lines of serial log:"
tail -100 "$SERIAL_LOG"
exit 4
#!/usr/bin/env bash
# AI-hint: bash Guards the T-230 syscall filter on usr/libexec/mios/mios-sandbox-exec.
# AI-doc: usr/share/doc/mios/manual/_harvest/tests_test_sandbox_seccomp_sh.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXEC="${ROOT}/usr/libexec/mios/mios-sandbox-exec"
GEN="${ROOT}/usr/libexec/mios/mios-seccomp-filter"

log() { printf '[test-sandbox-seccomp] %s\n' "$*"; }
die() { printf '[test-sandbox-seccomp] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { printf '[test-sandbox-seccomp]   [ OK ] %s\n' "$*"; }

[[ -f "$EXEC" ]] || die "wrapper not found at $EXEC"
[[ -f "$GEN"  ]] || die "generator not found at $GEN"

TMP="$(mktemp -d /tmp/mios-seccomp-test.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
export MIOS_VENDOR_TOML="${ROOT}/usr/share/mios/mios.toml"
export MIOS_SANDBOX_LOG="${TMP}/sandbox.log"

# ------------------------------------------------------------ generator tier --
log "generator tier"
python3 "$GEN" --out "${TMP}/f.bpf" || die "the generator failed on this host"
size="$(wc -c <"${TMP}/f.bpf")"
[[ "$size" -gt 0 && $((size % 8)) -eq 0 ]] \
    || die "the emitted program is not a whole number of sock_filters ($size bytes)"
ok "the filter builds ($size bytes, $((size / 8)) instructions)"

set +e
python3 "$GEN" --arch riscv64 --out "${TMP}/n.bpf" 2>/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || die "an unsupported architecture produced a filter instead of refusing"
[[ ! -s "${TMP}/n.bpf" ]] || die "an unsupported architecture wrote a filter anyway"
ok "an unsupported architecture is refused, not silently unfiltered ($rc)"

# Artifact assertions that need no bwrap, so the CI path stays a real gate.
# Manual ch62.
python3 - "$GEN" "${TMP}/f.bpf" <<'PYEOF' || die "the emitted program does not match its own denylist"
import os, struct, subprocess, sys, platform
sys.path.insert(0, os.path.join(os.getcwd(), "usr/lib/mios/agent-pipe"))
from mios_pipe.access import seccomp as S
gen, blob_path = sys.argv[1], sys.argv[2]
blob = open(blob_path, "rb").read()
ins = [struct.unpack("<HBBI", blob[i:i + 8]) for i in range(0, len(blob), 8)]
want_arch = S.AUDIT_ARCH[platform.machine()]
assert ins[1][3] == want_arch, f"arch word {ins[1][3]:#x} != {want_arch:#x}"
out = subprocess.run([sys.executable, gen, "--describe"], capture_output=True, text=True).stdout
denied = int([w.split("=")[1] for w in out.split() if w.startswith("denied=")][0])
assert denied > 0, "the filter denies nothing"
assert len(ins) == 3 + denied + 2, f"{len(ins)} instructions for {denied} denied"
assert ins[1][2] == denied + 1, "an arch mismatch does not fall through to deny"
print(f"  arch={want_arch:#x} denied={denied} insns={len(ins)}")
PYEOF
ok "the emitted program names this host's arch and matches its denylist"

desc="$(python3 "$GEN" --describe)"
for sc in ptrace mount chroot init_module bpf keyctl; do
    grep -q " ${sc}$" <<<"$desc" || die "the baseline floor lost ${sc}"
done
ok "the baseline floor is intact (ptrace, mount, chroot, init_module, bpf, keyctl)"
grep -q " swapon$" <<<"$desc" || die "the SSOT [sandbox].seccomp_deny list did not extend the floor"
ok "the SSOT list extends the floor"

log "refusal tier: no generator => enforce must REFUSE, never run unfiltered"
stub="${TMP}/bin"; mkdir -p "$stub"
cp "$EXEC" "${stub}/mios-sandbox-exec"
set +e
PATH="/usr/bin:/bin" bash "${stub}/mios-sandbox-exec" --level enforce \
    --workspace "$TMP" -- /bin/true 2>"${TMP}/err"; rc=$?
set -e
[[ "$rc" -eq 126 ]] || die "expected refusal 126 with no generator beside the wrapper, got $rc"
grep -q "refusing to run with no syscall filter" "${TMP}/err" \
    || die "the refusal did not say why: $(cat "${TMP}/err")"
ok "with no generator, level=enforce refuses (126) instead of running unfiltered"

# ------------------------------------------------------------------ live tier --
# A kernel that refuses bwrap is an ENVIRONMENT fact, so the live tier skips
# loudly even under REQUIRE_TOOLS. Manual ch62.
if ! command -v bwrap >/dev/null 2>&1; then
    log "SKIP live tier: bwrap absent"
    log "PASS (generator tier only)"
    exit 0
fi
if ! bwrap --ro-bind / / --die-with-parent /bin/true >/dev/null 2>&1; then
    log "SKIP live tier: bwrap installed but this kernel/policy refuses it --"
    log "      $(bwrap --ro-bind / / --die-with-parent /bin/true 2>&1 | head -1)"
    log "PASS (generator tier only)"
    exit 0
fi

log "live tier: $(bwrap --version 2>/dev/null || echo bwrap)"
ws="${TMP}/ws"; mkdir -p "$ws"

# Some runners cannot configure loopback in a fresh net namespace; that is the
# RUNNER, not the sandbox. Probe once, fall back to --net. Manual ch62.
NET_ARG=()
if ! bwrap --ro-bind / / --dev /dev --unshare-net --die-with-parent \
        /bin/true >/dev/null 2>&1; then
    NET_ARG=(--net)
    log "NOTE: this host cannot unshare the net namespace under bwrap;"
    log "      running the confined checks WITH the network (seccomp unaffected)"
fi

run_confined() {
    bash "$EXEC" --level enforce "${NET_ARG[@]}" --workspace "$ws" -- /bin/sh -c "$1" 2>&1
}

# bwrap works (checked above), so a failure HERE is the wrapper's.
probe="$(run_confined 'echo PROBE=up')" || true
grep -q "PROBE=up" <<<"$probe" \
    || die "bwrap runs, but the wrapper could not start a confined command: $probe"

out="$(run_confined '
    echo "PID1=$(cat /proc/1/comm)"
    grep -i "^Seccomp:" /proc/self/status | tr -d " \t"
    chroot /tmp /bin/true 2>&1 | sed "s/^/CHROOT=/"
    echo "WORK=$(echo alive)"
    touch ./inside && echo "WS=writable"
    touch /etc/mios-seccomp-probe 2>/dev/null && echo "OUTSIDE=writable" || echo "OUTSIDE=denied"
')" || true

grep -q "PID1=bwrap" <<<"$out" || die "the process tree does not show the wrapper: $out"
ok "the confined process really runs under bwrap"

grep -qE "Seccomp:2" <<<"$out" || die "no seccomp filter is loaded (Seccomp should be 2): $out"
ok "a seccomp filter IS loaded in the confined process (mode 2 = filter)"

grep -qi "CHROOT=.*not permitted" <<<"$out" \
    || die "chroot() was not denied by the filter: $out"
ok "a denied syscall returns EPERM instead of succeeding"

grep -q "WORK=alive" <<<"$out" || die "the filter broke ordinary work: $out"
ok "ordinary work still runs under the filter"
grep -q "WS=writable" <<<"$out" || die "the workspace is not writable: $out"
grep -q "OUTSIDE=denied" <<<"$out" || die "a path outside the bind set was writable: $out"
ok "the filesystem jail still holds (workspace writable, outside denied)"

[[ ! -e /etc/mios-seccomp-probe ]] || die "the sandbox leaked a write to /etc"
ok "nothing leaked out of the sandbox"

log "PASS (generator + live tiers)"

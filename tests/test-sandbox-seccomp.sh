#!/usr/bin/env bash
# AI-hint: Guards the T-230 syscall filter on usr/libexec/mios/mios-sandbox-exec. Two tiers: a generator tier that always runs (the filter builds, an unsupported architecture is REFUSED rather than silently unfiltered, and the SSOT list extends the baseline floor), and a live tier under a real bwrap that proves the thing the roadmap asked for -- the confined process reports a loaded filter instead of `Seccomp: 0`, a denied syscall returns EPERM instead of succeeding, ordinary work still runs, and the filesystem/network jail still holds. Also asserts the refusal stance: with the generator unavailable, level=enforce must EXIT rather than run a verb with no filter.
# AI-related: usr/libexec/mios/mios-sandbox-exec, usr/libexec/mios/mios-seccomp-filter, usr/lib/mios/agent-pipe/mios_pipe/access/seccomp.py, usr/share/mios/mios.toml
# AI-functions: log, die, ok, run_confined
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
if ! command -v bwrap >/dev/null 2>&1; then
    if [[ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" == "1" ]]; then
        die "bwrap absent and MIOS_DRIFT_REQUIRE_TOOLS=1 -- the live tier cannot be skipped"
    fi
    log "SKIP live tier: bwrap absent (set MIOS_DRIFT_REQUIRE_TOOLS=1 to make this fatal)"
    log "PASS (generator tier only)"
    exit 0
fi

log "live tier: $(bwrap --version 2>/dev/null || echo bwrap)"
ws="${TMP}/ws"; mkdir -p "$ws"
run_confined() {
    bash "$EXEC" --level enforce --workspace "$ws" -- /bin/sh -c "$1" 2>&1
}

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

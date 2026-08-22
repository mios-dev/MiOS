#!/usr/bin/env bash
# AI-hint: Proves the greenboot AI-plane check skips a unit this blade does not activate. `systemctl is-enabled` reports INSTALLATION, not whether a unit will start -- Condition* is evaluated at start time, so a capability-skipped unit still reads enabled (a Quadlet unit reads "generated", also exit 0). Without the marker guard a seat probes ports nothing is listening on, fails the required check and rolls itself back on every boot. Runs the real _blade_activates against a real fixture tree; no systemd needed.
# AI-related: usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh, usr/libexec/mios/role-apply, usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh"
PASS=0

log()  { printf '[greenboot-blade-guard] %s\n' "$*"; }
die()  { printf '[greenboot-blade-guard] ERROR: %s\n' "$*" >&2; exit 1; }
ok()   { PASS=$((PASS + 1)); log "ok: $*"; }

[[ -r "$SCRIPT" ]] || die "probe script missing: $SCRIPT"

# Extract _blade_activates and run it against a fixture tree. Sourcing the whole
# script would execute its probes; this tests the predicate in isolation.
FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

sed -n '/^_blade_activates() {/,/^}/p' "$SCRIPT" > "${FIXTURE}/fn.sh"
[[ -s "${FIXTURE}/fn.sh" ]] || die "could not extract _blade_activates -- did it get renamed?"

mkdir -p "${FIXTURE}/usr/lib/systemd/system/mios-pgvector.service.d"
printf '[Unit]\nConditionPathExists=/etc/mios/blade.d/service-plane\n' \
    > "${FIXTURE}/usr/lib/systemd/system/mios-pgvector.service.d/50-blade-service-plane.conf"
mkdir -p "${FIXTURE}/usr/lib/systemd/system/mios-agent-pipe.service.d"   # no drop-in: ungated

# Rewrite the two absolute lookups onto the fixture so the real logic is exercised.
sed -e "s#/usr/lib/systemd/system/#${FIXTURE}/usr/lib/systemd/system/#g" \
    -e "s#/etc/mios/blade.d#${FIXTURE}/etc/mios/blade.d#g" \
    "${FIXTURE}/fn.sh" > "${FIXTURE}/fn2.sh"
# shellcheck disable=SC1091
. "${FIXTURE}/fn2.sh"

mkdir -p "${FIXTURE}/etc/mios/blade.d"

# --- a seat: markers directory exists, service-plane marker absent -----------
MIOS_BLADE_CAPS="" _blade_activates mios-pgvector.service \
    && die "a seat must NOT probe mios-pgvector: its capability marker is absent"
ok "seat skips a capability-gated unit"

MIOS_BLADE_CAPS="" _blade_activates mios-agent-pipe.service \
    || die "an ungated unit must still be probed on a seat"
ok "seat still probes the ungated front door"

# --- a serving blade: the marker is present ---------------------------------
touch "${FIXTURE}/etc/mios/blade.d/service-plane"
MIOS_BLADE_CAPS="service-plane" _blade_activates mios-pgvector.service \
    || die "a blade granting service-plane MUST probe mios-pgvector"
ok "serving blade probes the gated unit"

# --- degrade open: no resolver output at all (Law 12) ------------------------
rm -rf "${FIXTURE}/etc/mios/blade.d"
MIOS_BLADE_CAPS="" _blade_activates mios-pgvector.service \
    || die "with no blade.d at all the check must degrade OPEN and probe"
ok "degrades open when the blade resolver has not run"

log "PASS: ${PASS}/4 assertions"

#!/usr/bin/env bash
# AI-hint: bash Proves role-apply's five-tier role ladder against fixtures, running the REAL functions extracted from the shipped script.
# AI-doc: usr/share/doc/mios/manual/tests.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/usr/libexec/mios/role-apply"
LIB="${ROOT}/usr/lib/mios/blade.sh"
PASS=0

log() { printf '[role-apply-precedence] %s\n' "$*"; }
die() { printf '[role-apply-precedence] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { PASS=$((PASS + 1)); log "ok: $*"; }

[[ -r "$SCRIPT" ]] || die "role-apply missing: $SCRIPT"
[[ -r "$LIB" ]]    || die "blade.sh missing: $LIB"
grep -q 'blade\.sh' "$SCRIPT" || die "role-apply no longer sources the shared resolver"

FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

# The REAL library, driven against a fixture tree. role-apply itself would try
# to set the hostname and talk to systemd; the resolver it sources does not.
# Read by the sourced resolver, not by this file.
export ROLE_CONF="${FIXTURE}/role.conf"
export CMDLINE_FILE="${FIXTURE}/cmdline"
export BLADE_D="${FIXTURE}/blade.d"
# shellcheck source=/dev/null
source "$LIB"
: > "$ROLE_CONF"
: > "$CMDLINE_FILE"

# Values the SSOT query would export. hybrid is the shipped [blade].type, so
# `mios.blade=hybrid` on the cmdline is the GENERATED karg, not a choice.
export SSOT_TYPE="hybrid"
export SSOT_FALLBACK="headless"
export SSOT_ARCHETYPES="compute controller desktop endpoint ha-node headless hybrid k3s-master"
export SSOT_CAPS_LEGAL="controller gpu-serving service-plane"
export SSOT_ALIASES="ha=ha-node k3s=k3s-master"

# Normal hardware for the ladder tests; the real _hw_demotion is exercised on
# its own below, and re-stubbed to fire for the tier-precedence cases.
_hw_demotion() { :; }

set_cmdline() { printf '%s\n' "$1" > "$CMDLINE_FILE"; }
set_conf()    { printf '%s\n' "$1" > "$ROLE_CONF"; }
role()        { _resolve_role | cut -f1; }
source_of()   { _resolve_role | cut -f2; }

# --- tier 3: the vendor default ---------------------------------------------
set_cmdline "root=UUID=x ro"; : > "$ROLE_CONF"
[[ "$(role)" == "hybrid" ]] || die "bare cmdline must resolve [blade].type, got '$(role)'"
[[ "$(source_of)" == "[blade].type" ]] || die "wrong source: $(source_of)"
ok "no karg, no role.conf -> [blade].type"

set_cmdline "root=UUID=x ro mios.blade=hybrid"
[[ "$(role)" == "hybrid" ]] || die "the generated karg must still resolve hybrid"
ok "the generated karg agrees with the vendor tier"

# --- tier 2: /etc/mios/role.conf beats the GENERATED karg (the regression) ---
set_cmdline "root=UUID=x ro mios.blade=hybrid"
set_conf 'ROLE="desktop"'
[[ "$(role)" == "desktop" ]] \
    || die "role.conf must outrank the generated karg (this is what killed \`mios blade set\`), got '$(role)'"
[[ "$(source_of)" == "$ROLE_CONF" ]] || die "wrong source: $(source_of)"
ok "role.conf outranks the generated karg -- \`mios blade set\` works again"

# --- tier 1: an EXPLICIT karg outranks role.conf ----------------------------
set_cmdline "root=UUID=x ro mios.blade=hybrid mios.blade=compute"
[[ "$(role)" == "compute" ]] || die "an explicit karg must win over role.conf, got '$(role)'"
[[ "$(source_of)" == "cmdline" ]] || die "wrong source: $(source_of)"
ok "an explicit karg outranks role.conf (and last token wins)"

set_cmdline "root=UUID=x ro mios.role=controller"
[[ "$(role)" == "controller" ]] || die "mios.role= must be honoured too, got '$(role)'"
ok "mios.role= is accepted as an alias for mios.blade="

# --- tier 4: the hardware demotion corrects tier 3, never tiers 1-2 ---------
_hw_demotion() { printf 'no-drm'; }
set_cmdline "root=UUID=x ro mios.blade=hybrid"; : > "$ROLE_CONF"
[[ "$(role)" == "headless" ]] || die "graphics-less hardware must demote the vendor guess, got '$(role)'"
[[ "$(source_of)" == "hardware:no-drm" ]] || die "wrong source: $(source_of)"
ok "hardware demotes the vendor tier (reachable again)"

set_conf 'ROLE="desktop"'
[[ "$(role)" == "desktop" ]] || die "hardware must NOT overrule an admin's role.conf, got '$(role)'"
set_cmdline "root=UUID=x ro mios.blade=desktop"; : > "$ROLE_CONF"
[[ "$(role)" == "desktop" ]] || die "hardware must NOT overrule an explicit karg, got '$(role)'"
ok "hardware never overrules an explicit choice"
_hw_demotion() { :; }

# The real predicate, on its own: WSL demotes.
awk '/^_hw_demotion\(\) \{/,/^\}/' "$LIB" | sed 's/^_hw_demotion()/_hw_demotion_real()/' \
    > "${FIXTURE}/hw.sh"
# shellcheck disable=SC1091
. "${FIXTURE}/hw.sh"
[[ "$(export VIRT=wsl IS_BLACKWELL=false; _hw_demotion_real)" == "wsl" ]] \
    || die "the real _hw_demotion must report the wsl reason"
[[ -z "$(export VIRT=wsl IS_BLACKWELL=false SSOT_FALLBACK=""; _hw_demotion_real)" ]] \
    || die "with no [blade].fallback the sniff must refuse to guess an archetype"
ok "the hardware sniff reports a reason and refuses to guess without [blade].fallback"

# --- the Law-12 floor is the cmdline, not a baked-in archetype name ---------
set_cmdline "root=UUID=x ro mios.blade=hybrid"; : > "$ROLE_CONF"
[[ "$(export SSOT_TYPE="" SSOT_FALLBACK=""; role)" == "hybrid" ]] \
    || die "with an unreadable SSOT the generated karg must still supply the role"
[[ "$(export SSOT_TYPE="" SSOT_FALLBACK=""; source_of)" == "cmdline" ]] \
    || die "wrong source for the cmdline floor"
set_cmdline "root=UUID=x ro"
[[ -z "$(export SSOT_TYPE="" SSOT_FALLBACK=""; role)" ]] \
    || die "with neither an SSOT nor a karg the resolver must return nothing, not a guess"
ok "the Law-12 floor is the generated karg; nothing is invented"

# --- FEATURES are unioned, not replaced -------------------------------------
set_cmdline "root=UUID=x ro mios.blade=hybrid mios.features=gpu-serving"
set_conf 'ROLE="desktop"
FEATURES="controller"'
FEATS="$(_resolve_features)"
[[ "$FEATS" == "gpu-serving,controller" ]] \
    || die "features must union cmdline + role.conf, got '$FEATS'"
ok "features union across tiers -- \`mios blade add-capability\` survives a reboot"

# --- role.conf is PARSED, never sourced -------------------------------------
set_conf 'ROLE="desktop"
FEATURES="$(touch '"${FIXTURE}"'/pwned)"'
_conf_get "$ROLE_CONF" FEATURES >/dev/null
[[ ! -e "${FIXTURE}/pwned" ]] || die "_conf_get executed the file -- it must parse, not source"
[[ "$(_conf_get "$ROLE_CONF" ROLE)" == "desktop" ]] || die "_conf_get lost ROLE"
ok "role.conf is parsed, not executed"

# --- aliases are data, not a case-statement glob ----------------------------
[[ "$(_canon_role k3s)" == "k3s-master" ]] || die "alias k3s -> k3s-master failed"
[[ "$(_canon_role ha)"  == "ha-node"    ]] || die "alias ha -> ha-node failed"
[[ "$(_canon_role k3sx)" == "k3sx"      ]] || die "k3sx must NOT glob onto k3s-master"
ok "role aliases resolve exactly, no globbing"

# --- capabilities are a closed set ------------------------------------------
_is_legal_cap "service-plane" || die "service-plane must be legal"
! _is_legal_cap "ai"          || die "'ai' (the retired [profile].features value) must be refused"
! _is_legal_cap "k3s"         || die "'k3s' must be refused as a capability"
ok "unknown capability names are refused"

# --- the target is derived, not enumerated ----------------------------------
[[ "$(_target_for headless)" == "mios-headless.target" ]] || die "_target_for is wrong"
for a in $SSOT_ARCHETYPES; do
    t="$(_target_for "$a")"
    [[ -f "${ROOT}/usr/lib/systemd/system/${t}" ]] || die "archetype '$a' has no shipped ${t}"
done
ok "every archetype's derived target is a shipped unit"

log "PASS: ${PASS}/14 assertions"

#!/usr/bin/bash
# AI-hint: Shared blade-resolution library. ONE implementation of the archetype ladder, the capability set and the alias table, sourced by usr/libexec/mios/role-apply (boot-time resolver) and usr/libexec/mios/mios-blade (the day-2 verb) so the two cannot drift. Every input is parameterized -- cmdline file, role.conf path, marker directory -- so tests/test-role-apply-precedence.sh drives the real functions rather than a copy.
# AI-related: usr/libexec/mios/role-apply, usr/libexec/mios/mios-blade, usr/share/mios/mios.toml, usr/lib/bootc/kargs.d/05-mios-blade.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md
# AI-functions: _cmdline_tok, _conf_get, _ssot_query, _hw_demotion, _resolve_role, _canon_role, _caps_for, _is_legal_cap, _resolve_features, _target_for
#
# Callers may pre-set ROLE_CONF / BLADE_D / CMDLINE_FILE; otherwise the FHS
# defaults below apply.

: "${ROLE_CONF:=${MIOS_ETC_DIR:-/etc/mios}/role.conf}"
: "${BLADE_D:=${MIOS_ETC_DIR:-/etc/mios}/blade.d}"
: "${CMDLINE_FILE:=/proc/cmdline}"

# Last `key=value` token on the kernel command line wins: bootc concatenates
# kargs.d in file order.
_cmdline_tok() {
    local key="$1" tok out=""
    [[ -r "$CMDLINE_FILE" ]] || return 0
    for tok in $(< "$CMDLINE_FILE"); do
        case "$tok" in
            "${key}="*) out="${tok#"${key}"=}" ;;
        esac
    done
    printf '%s' "$out"
}

# Read one KEY from a bare KEY=value file WITHOUT sourcing it: `.` would run
# it as root and clobber the names it sets.
_conf_get() {
    local file="$1" key="$2" val=""
    [[ -r "$file" ]] || return 0
    val="$(sed -n "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//p" "$file" | tail -1)"
    val="${val%\"}"; val="${val#\"}"
    val="${val%\'}"; val="${val#\'}"
    printf '%s' "$val"
}

# One SSOT call, emitting shell assignments for `eval`. Empty on any failure,
# so an unreadable SSOT still boots.
_ssot_query() {
    python3 - <<'PY' 2>/dev/null || true
import os
import shlex
import sys

sys.path.insert(0, os.environ.get("MIOS_USR_DIR", "/usr/lib/mios"))
import mios_toml  # noqa: E402

blade = (mios_toml.load_merged().get("blade") or {})
arche = blade.get("archetypes") or {}
alias = blade.get("role_aliases") or {}


def flat(value):
    return [value] if isinstance(value, str) else list(value or [])


legal = sorted({c for caps in arche.values() for c in flat(caps) if c})
print("SSOT_TYPE=%s" % shlex.quote(str(blade.get("type") or "")))
print("SSOT_FALLBACK=%s" % shlex.quote(str(blade.get("fallback") or "")))
print("SSOT_ARCHETYPES=%s" % shlex.quote(" ".join(sorted(arche))))
print("SSOT_CAPS_LEGAL=%s" % shlex.quote(" ".join(legal)))
print("SSOT_ALIASES=%s" % shlex.quote(
    " ".join("%s=%s" % (k, v) for k, v in sorted(alias.items()))))
for name, caps in sorted(arche.items()):
    var = "".join(ch if ch.isalnum() else "_" for ch in name).upper()
    print("SSOT_ARCH_%s=%s" % (var, shlex.quote(" ".join(flat(caps)))))
PY
}

# A safety demotion applied to tier 3 only. Emits a REASON; what it demotes TO
# is [blade].fallback, and with none it demotes to nothing.
# Callers set VIRT and IS_BLACKWELL.
_hw_demotion() {
    [[ -n "${SSOT_FALLBACK:-}" ]] || return 0
    if [[ "${VIRT:-}" == "wsl" || -e /dev/dxg ]]; then
        printf 'wsl'
    elif [[ "${IS_BLACKWELL:-false}" == "true" ]]; then
        printf 'blackwell-safety'
    elif ! compgen -G "/dev/dri/renderD*" >/dev/null && [[ ! -e /sys/class/drm/card0 ]]; then
        printf 'no-drm'
    fi
}

# The ladder, emitted as "role<TAB>source". Tiers, highest first:
#   1. mios.blade= / mios.role= on the cmdline, DIFFERENT from [blade].type
#   2. ROLE= in /etc/mios/role.conf                            (host tier)
#   3. [blade].type -- equivalently the generated karg       (vendor tier)
#   4. hardware demotion to [blade].fallback, tier 3 only
_resolve_role() {
    local karg conf
    karg="$(_cmdline_tok mios.blade)"
    [[ -n "$karg" ]] || karg="$(_cmdline_tok mios.role)"
    conf="$(_conf_get "$ROLE_CONF" ROLE)"

    if [[ -n "$karg" && "$karg" != "${SSOT_TYPE:-}" ]]; then
        printf '%s\t%s' "$karg" "cmdline"
        return 0
    fi
    if [[ -n "$conf" ]]; then
        printf '%s\t%s' "$conf" "$ROLE_CONF"
        return 0
    fi

    local vendor="${SSOT_TYPE:-}"
    if [[ -z "$vendor" ]]; then
        # No vendor tier and no karg: refuse to invent an archetype.
        printf '\t%s' "unresolved"
        return 0
    fi
    local demote
    demote="$(_hw_demotion)"
    if [[ -n "$demote" ]]; then
        printf '%s\t%s' "$SSOT_FALLBACK" "hardware:${demote}"
        return 0
    fi
    printf '%s\t%s' "$vendor" "[blade].type"
}

# [blade.role_aliases] maps a legacy spelling onto an archetype. Exact match
# only -- a glob would accept `k3sx` and resolve it to zero capabilities.
_canon_role() {
    local role="$1" pair
    for pair in ${SSOT_ALIASES:-}; do
        if [[ "$role" == "${pair%%=*}" ]]; then
            printf '%s' "${pair#*=}"
            return 0
        fi
    done
    printf '%s' "$role"
}

_caps_for() {
    local var
    var="SSOT_ARCH_$(printf '%s' "$1" | tr -c '[:alnum:]' '_' | tr '[:lower:]' '[:upper:]')"
    printf '%s' "${!var:-}"
}

_is_legal_cap() {
    local cap="$1" known
    for known in ${SSOT_CAPS_LEGAL:-}; do
        [[ "$cap" == "$known" ]] && return 0
    done
    return 1
}

# FEATURES are UNIONED across tiers, never replaced: blade.d is wiped on every
# role-apply run, so a skipped tier is a capability that vanishes.
_resolve_features() {
    printf '%s,%s' "$(_cmdline_tok mios.features)" "$(_conf_get "$ROLE_CONF" FEATURES)"
}

_target_for() {
    printf 'mios-%s.target' "$1"
}

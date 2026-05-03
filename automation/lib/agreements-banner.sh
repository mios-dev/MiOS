#!/usr/bin/env bash
# automation/lib/agreements-banner.sh -- single source of truth for the
# entry-point acknowledgment banner. Sourced by every shell-side entry
# point in 'MiOS' (mios.git) and 'mios-bootstrap' (mios-bootstrap.git).
#
# Prints a one-line note to stderr unless MIOS_AGREEMENT_BANNER=quiet is
# set in the environment. The banner is informational; invocation of the
# enclosing script is treated as acknowledgment of:
#   - LICENSE                 (Apache-2.0)
#   - LICENSES.md             (bundled-component licenses)
#   - CREDITS.md              (attribution registry)
#   - AGREEMENTS.md           (runtime agreements + research-project framing)
#
# Operators who require a hard interactive gate can set
# MIOS_REQUIRE_AGREEMENT_ACK=1 before invocation; the banner then prompts
# 'Acknowledge? [y/N]' and aborts with exit 78 (EX_CONFIG) on anything
# other than y / yes / Y / YES.

mios_print_agreement_banner() {
    case "${MIOS_AGREEMENT_BANNER:-}" in
        quiet|silent|off|0|false|FALSE) return 0 ;;
    esac
    local entry="${1:-${BASH_SOURCE[1]:-this entry point}}"
    entry="$(basename -- "$entry")"
    cat >&2 <<EOF
[mios] By invoking ${entry} you acknowledge AGREEMENTS.md
       (Apache-2.0 main + bundled-component licenses in LICENSES.md +
        attribution in CREDITS.md). 'MiOS' is a research project
       (pronounced 'MyOS'; generative, seed-script-derived).
EOF
    if [[ "${MIOS_REQUIRE_AGREEMENT_ACK:-}" == "1" ]]; then
        printf '[mios] Acknowledge? [y/N] ' >&2
        local reply=""
        if read -r reply; then
            case "$reply" in
                y|Y|yes|YES|Yes) ;;
                *)
                    echo "[mios] not acknowledged; aborting." >&2
                    exit 78
                    ;;
            esac
        else
            echo "[mios] no input available for ack prompt; aborting." >&2
            exit 78
        fi
    fi
}

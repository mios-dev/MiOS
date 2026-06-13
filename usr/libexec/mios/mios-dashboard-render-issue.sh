#!/usr/bin/env bash
# AI-hint: Composites the MiOS dashboard into /etc/issue.d/30-mios.issue so it
# AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, /usr/libexec/mios/mios-dashboard.sh, mios-dashboard-render-issue, mios-dashboard, mios-dashboard-issue, mios-motd, mios-dashboard-issue.service, mios-dashboard-issue.timer, multi-user.target
# /usr/libexec/mios/mios-dashboard-render-issue.sh
#
# Composites the MiOS dashboard into /etc/issue.d/30-mios.issue so it
# appears on the console BEFORE the login prompt. Handles the
# headless-first-console case (operator boots a fresh image, lands on
# tty1 / ttyS0 / IPMI SoL with no GUI, and needs to see the system
# state immediately).
#
# Triggered by:
#   - mios-dashboard-issue.service     (one-shot, after multi-user.target)
#   - mios-dashboard-issue.timer       (every 5 minutes thereafter, so
#                                       Quadlet-state changes propagate)
#
# Output is plain ASCII -- TERM=linux forces the dashboard's no-color
# path so the file is safe for kernel text VT, serial console, IPMI,
# and any other terminal that may not handle ANSI escape sequences
# cleanly.
#
# agetty reads /etc/issue and /etc/issue.d/* on each getty start, and
# `getty@.service` Restart=always ensures every login attempt re-reads
# the snippet, so refreshes from the timer always reach the next login.
set -uo pipefail

ISSUE_DIR=/etc/issue.d
ISSUE_FILE="${ISSUE_DIR}/30-mios.issue"
DASHBOARD=/usr/libexec/mios/mios-dashboard.sh

mkdir -p "$ISSUE_DIR" 2>/dev/null || true

if [[ ! -x "$DASHBOARD" ]]; then
    # Fail safe: write a minimal banner instead of leaving a stale
    # /etc/issue.d/30-mios.issue from a previous boot.
    {
        echo ""
        echo "  MiOS  --  dashboard renderer not present at ${DASHBOARD}"
        echo "  Login to inspect the system state via /etc/profile.d/zz-mios-motd.sh."
        echo ""
    } > "$ISSUE_FILE.new"
    mv -f "$ISSUE_FILE.new" "$ISSUE_FILE"
    chmod 0644 "$ISSUE_FILE"
    exit 0
fi

# Render in plain ASCII to a temp file, then atomic-rename so partial
# writes never reach getty. Invoked through explicit `env -i bash` to
# break the SHELLOPTS chain -- without it, mios-dashboard.sh inherits
# `nounset:pipefail` from this wrapper's exported SHELLOPTS and exits
# silently with rc=1 during one of its early `tput cols` / `((...))`
# paths when stdin is not a TTY (systemd context). With the clean env,
# the dashboard runs as if from a login shell.
#
# Render is best-effort: a getty without a banner is a cosmetic glitch,
# but a FAILED unit clutters every cockpit dashboard refresh and
# triggers needless restart-loops via the timer. So on render failure,
# we drop a minimal banner instead of exiting non-zero.
if TERM=linux env -i PATH="$PATH" TERM=linux bash "$DASHBOARD" \
        --no-color --services-only > "$ISSUE_FILE.new" 2>/dev/null \
   && [[ -s "$ISSUE_FILE.new" ]]; then
    chmod 0644 "$ISSUE_FILE.new"
    mv -f "$ISSUE_FILE.new" "$ISSUE_FILE"
else
    rm -f "$ISSUE_FILE.new"
    {
        echo ""
        echo "  MiOS  --  console banner (dashboard render skipped this tick)"
        echo "  Login for live system state -- /etc/profile.d/zz-mios-motd.sh"
        echo ""
    } > "$ISSUE_FILE.tmp"
    chmod 0644 "$ISSUE_FILE.tmp"
    mv -f "$ISSUE_FILE.tmp" "$ISSUE_FILE"
fi

exit 0

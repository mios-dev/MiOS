#!/usr/bin/env bash
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
# writes never reach getty.
TERM=linux "$DASHBOARD" --no-color --services-only > "$ISSUE_FILE.new" 2>/dev/null || {
    rm -f "$ISSUE_FILE.new"
    exit 1
}
chmod 0644 "$ISSUE_FILE.new"
mv -f "$ISSUE_FILE.new" "$ISSUE_FILE"

exit 0

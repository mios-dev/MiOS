#!/bin/bash
# First-time-effective Google sign-in for the Antigravity CLI (agy) in a
# headless container. Antigravity has no non-interactive auth, so this script
# drives agy's interactive TUI inside tmux through every first-run screen
# (login method → OAuth URL → authorization code → color scheme → Terms of
# Service → workspace trust → main prompt) and verifies the result.
#
# The whole flow is two commands:
#
#   bash agy-login.sh                      # step 1: prints the Google auth URL
#   bash agy-login.sh --code '<code>'      # step 2: submits the code, finishes
#                                          #         onboarding, runs the probe
#
# Flags:
#   --code <code>   authorization code from the Google consent page
#   --telemetry     leave Google's "share Interactions data" checkbox ON
#                   (default: OFF — consent belongs to the human; re-enable
#                   any time in agy settings)
#   --no-trust      answer "No, exit" at the workspace-trust prompt (the
#                   credential is still cached; agy just won't operate here)
#   --status        run the doctor (with live probe) and exit
#   --tmux          force the tmux driver even on a real terminal
#
# On a real terminal with no flags, plain `agy` is exec'd instead — its native
# flow handles everything, including remote/SSH URL display.
#
# The screen patterns below were captured from a live agy 1.2.6 first run.
# TUIs drift: on any unrecognized screen the driver dumps the pane with manual
# tmux instructions instead of guessing (exit 3).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
SESSION=agy-login

CODE=""; TELEMETRY=0; TRUST=1; FORCE_TMUX=0; STATUS=0
while [ $# -gt 0 ]; do
    case "$1" in
        --code) CODE="${2:?--code needs a value}"; shift;;
        --telemetry) TELEMETRY=1;;
        --no-trust) TRUST=0;;
        --status) STATUS=1;;
        --tmux) FORCE_TMUX=1;;
        *) echo "unknown flag: $1 (see header of $0)" >&2; exit 64;;
    esac
    shift
done

command -v agy >/dev/null 2>&1 || { echo "agy not installed — run: bash $SCRIPT_DIR/setup-antigravity.sh" >&2; exit 69; }
[ "$STATUS" = 1 ] && exec bash "$SCRIPT_DIR/agy-doctor.sh" --probe

# The keyring must be up BEFORE agy runs, or the fresh credential lands nowhere.
# shellcheck source=agy-keyring.sh
. "$SCRIPT_DIR/agy-keyring.sh"

# Humans at a real terminal: agy's native flow is the best UX.
if [ -t 0 ] && [ -t 1 ] && [ "$FORCE_TMUX" = 0 ] && [ -z "$CODE" ]; then
    echo "Starting interactive agy — it shows a Google authorization URL if no browser opens."
    exec agy
fi

command -v tmux >/dev/null 2>&1 || { echo "tmux required for the headless driver — run setup-antigravity.sh" >&2; exit 69; }

pane() { tmux capture-pane -p -J -t "$SESSION" 2>/dev/null; }   # visible pane only, wrapped lines joined
send() { tmux send-keys -t "$SESSION" "$@"; }
die_unknown() {
    echo "----- unrecognized agy screen (TUI may have changed) -----" >&2
    pane | grep -v '^ *$' >&2 || true
    cat >&2 <<EOF
-----------------------------------------------------------
Drive it manually, then re-run this script:
  watch:  tmux capture-pane -pJ -t $SESSION
  type:   tmux send-keys -t $SESSION -l '<text>'   (then: tmux send-keys -t $SESSION Enter)
  reset:  tmux kill-session -t $SESSION && bash $0
EOF
    exit 3
}

tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" -x 220 -y 50 "agy"

CODE_SENT=0
URL=""
for _ in $(seq 1 40); do
    sleep 3
    P="$(pane)" || die_unknown

    # Already signed in: the main prompt appears without any auth screens.
    if printf '%s' "$P" | grep -q '? for shortcuts'; then
        if [ "$CODE_SENT" = 1 ] || [ -z "$CODE" ]; then
            acct="$(printf '%s' "$P" | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+' | head -1)"
            send -l '/quit'; send Enter; sleep 2
            tmux kill-session -t "$SESSION" 2>/dev/null || true
            echo "Signed in${acct:+ as $acct}. Verifying headless auth end to end..."
            exec bash "$SCRIPT_DIR/agy-doctor.sh" --probe
        fi
        # --code given but agy never asked for one → it was already authenticated.
        CODE=""
        continue

    elif printf '%s' "$P" | grep -q 'Select login method'; then
        send Enter                                    # "> 1. Google OAuth"

    elif printf '%s' "$P" | grep -qi 'paste the authorization code'; then
        if [ -n "$CODE" ] && [ "$CODE_SENT" = 0 ]; then
            send -l "$CODE"; send Enter; CODE_SENT=1
        elif [ "$CODE_SENT" = 0 ]; then
            URL="$(printf '%s' "$P" | grep -o 'https://accounts\.google\.com[^[:space:]]*' | head -1)"
            [ -n "$URL" ] || die_unknown
            cat <<EOF

============================ ACTION REQUIRED ============================
Open this URL in YOUR browser, sign in with Google, copy the code shown:

$URL

Then finish with:
  bash $0 --code '<paste the code here>'
=========================================================================
agy keeps waiting in tmux session '$SESSION'; the URL stays valid until
the session is reset.
EOF
            exit 0
        fi
        # code sent: fall through and wait for the next screen

    elif printf '%s' "$P" | grep -q 'Choose your color scheme'; then
        send Enter                                    # accept default (terminal)

    elif printf '%s' "$P" | grep -q 'Terms of Service'; then
        # Checkbox = optional "share Interactions data with Google" consent.
        # Left OFF unless --telemetry: consent is the human's to give.
        if [ "$TELEMETRY" = 0 ] && printf '%s' "$P" | grep -q '\[x\]'; then
            send Enter; sleep 1                       # toggle off
        elif [ "$TELEMETRY" = 1 ] && printf '%s' "$P" | grep -q '\[ \]'; then
            send Enter; sleep 1                       # toggle on
        fi
        send Down Down Right; sleep 1; send Enter     # checkbox → [Done]

    elif printf '%s' "$P" | grep -q 'Do you trust the contents'; then
        if [ "$TRUST" = 1 ]; then
            send Enter                                # "> Yes, I trust this folder"
        else
            send Down; sleep 1; send Enter            # "No, exit"
            echo "Workspace not trusted (--no-trust); credential is cached, agy exited."
            tmux kill-session -t "$SESSION" 2>/dev/null || true
            exec bash "$SCRIPT_DIR/agy-doctor.sh" --probe
        fi

    elif printf '%s' "$P" | grep -qiE 'auth.*(fail|expired|invalid)|invalid.*code'; then
        echo "Authentication failed — the code may be expired or mistyped." >&2
        pane | grep -v '^ *$' | tail -8 >&2 || true
        echo "Reset and retry: tmux kill-session -t $SESSION && bash $0" >&2
        exit 1

    elif printf '%s' "$P" | grep -qiE 'Waiting for authentication|Welcome to the Antigravity'; then
        :                                             # splash / transition: just wait
    else
        :                                             # partial redraw: give it one more tick
    fi
done

echo "Timed out after ~120s without reaching a known state." >&2
die_unknown

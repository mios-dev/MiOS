#!/usr/bin/env sh
# agy_host.sh — launch Google Antigravity (agy) as the L0 manager of a dev-loop
# run (topology A in references/harness-adapters.md §3): AGY decomposes, owns
# shared state, dispatches the lanes in <lanes.json> through scripts/devloop.sh
# (any mix of harnesses — multiple antigravity AND multiple claude-code lanes
# side by side), runs the two-sided merge gates itself, merges, reports.
#
#   sh scripts/agy_host.sh <lanes.json>                          # interactive manager
#   sh scripts/agy_host.sh <lanes.json> --headless [--yolo]      # unattended, SINGLE-TURN
#   sh scripts/agy_host.sh <lanes.json> --session  [--yolo]      # unattended, HELD SESSION
#   sh scripts/agy_host.sh <lanes.json> --print-prompt           # just emit the manager prompt
#
# --headless vs --session is about PROCESS LIFETIME, not about being unattended.
# --headless is `agy -p`: one turn, then the process exits and anything it started
# that had not finished dies with it. --session holds a stream-json NDJSON session
# open across turns (scripts/agy_session.py), so native subagent lanes survive the
# turn that dispatched them and the host can poll until they report.
#
# Requirements: `agy` installed and authenticated once on this machine
# (scripts/env/setup-antigravity.sh + scripts/env/agy-login.sh),
# and — for parallel lanes — a live Secret Service keyring so every spawned
# `agy -p` lane reuses the cached credential instead of re-asking.
# The agy flag surface drifts monthly; run `python3 scripts/adapters.py probe` first.
set -eu

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
LANES=${1:-}
[ -n "$LANES" ] && [ -f "$LANES" ] || { echo "usage: sh scripts/agy_host.sh <lanes.json> [--headless|--session [--yolo]] [--tmux] [--print-prompt]" >&2; exit 64; }
LANES=$(cd "$(dirname "$LANES")" && pwd)/$(basename "$LANES")
shift
MODE=interactive; SKIP_PERMS=0; HEADLESS=0; SESSION=0; PRINT_ONLY=0; USE_TMUX=0
# Three axes, tracked separately on purpose, because folding them together makes the
# behaviour depend on the ORDER the flags were typed in:
#   MODE       - which executor runs the prompt (interactive / headless / session)
#   HEADLESS   - which dispatch rule the prompt must carry
#   PRINT_ONLY - a sticky override: preview the prompt, execute nothing
# PRINT_ONLY is deliberately NOT a MODE value. When it was, `--print-prompt --headless`
# set MODE=print and then MODE=headless and LAUNCHED the manager the operator was only
# trying to preview -- a dry-run flag that runs the thing is the worst kind of surprise,
# and adding --session made it worse. --print-prompt now wins wherever it appears.
while [ $# -gt 0 ]; do
    case "$1" in
        --headless) MODE=headless; HEADLESS=1;;
        --session) MODE=session; HEADLESS=1; SESSION=1;;
        --tmux) USE_TMUX=1;;
        --yolo) SKIP_PERMS=1;;
        --print-prompt) PRINT_ONLY=1;;
        *) echo "unknown flag: $1" >&2; exit 64;;
    esac
    shift
done
[ "$PRINT_ONLY" = 1 ] && MODE=print

# Validate the lane file before handing it to a model: fail here, not mid-run.
python3 "$SKILL_DIR/scripts/adapters.py" validate "$LANES" >/dev/null || { echo "lane file failed validation: $LANES" >&2; exit 65; }

# The run's repository root: everything the manager creates lives under it.
# (An agy manager perceives its TRUSTED WORKSPACE as home and, unanchored,
# invents paths in the wrong checkout — observed live 2026-09.)
RUN_ROOT=$(cd "$(dirname "$LANES")" && git rev-parse --show-toplevel 2>/dev/null || dirname "$LANES")

# Cloud containers keep the keyring's bus address in this env file; without it
# agy (and every agy -p lane it spawns) cannot see the cached credential and
# stalls on authentication. No-op where the file does not exist.
[ -f "$HOME/.config/agy-cloud/keyring.env" ] && . "$HOME/.config/agy-cloud/keyring.env"

# How the manager dispatches its OWN lanes. This is decided by PROCESS LIFETIME, not by
# whether a human is watching, and it is not a preference.
#
# `agy -p` is single-turn print mode: the turn ends when the model stops speaking, and the
# process exits. Observed live (agy 1.2.6): the manager wrote lanes.external.json,
# provisioned all three worktrees, invoked the first native lane, and ended its turn saying
# it was "waiting" for the lane to report -- leaving three worktrees at dirty=0
# commits_ahead=0, no .devloop/native/ reports, and no agy process alive. It cannot detect
# this, because from inside the turn the dispatch succeeded.
#
# What that observation does and does not establish (measured 1.2.6, three probes, two of
# which refuted the first explanation): invoke_subagent is NOT unavailable headlessly. It
# succeeds under single-shot -p, inside a held session, and with no prior define_subagent,
# all with denied_actions absent -- and it still succeeds when an invalid toolPermission
# voids settings.json and permission_mode degrades to request-review, which eliminates the
# leading suspect. It is ungated by construction: the permission grammar has five actions
# (read_file, write_file, command, url, mcp) and invoke_subagent is not one of them.
# Every subagent in those probes finished INSIDE the dispatching turn.
#
# So the real constraint is lifetime, exactly as the original comment argued: a subagent
# that has not finished when the turn ends is lost. Single-shot mode therefore still routes
# everything through the foreground orchestrator. A HELD session does not have that problem
# -- the process outlives any single turn -- so --session is allowed native lanes and
# agy_session.py polls until each one has written its report.
# The manager prompt is a CANNED TEMPLATE, not a shell string. Prompt text assembled inside a
# double-quoted assignment produced, in one week: 25 variables reaching the model unexpanded, a
# runtime exit 127 when a pair of quotes inside the text closed the assignment early (sh -n
# passes -- the result is still valid shell), and an instruction to pass a WaitMsBeforeAsync
# value that had already been measured impossible, surviving in a branch nobody diffed.
# prompt.py refuses all three: undeclared placeholder, missing value, and any $SHELL_VAR
# reaching the rendered output.
PROMPTS="$SKILL_DIR/scripts/prompt.py"
if [ "$SESSION" = 1 ]; then   DISPATCH_TEMPLATE=dispatch.session
elif [ "$HEADLESS" = 1 ]; then DISPATCH_TEMPLATE=dispatch.headless
else                           DISPATCH_TEMPLATE=dispatch.interactive
fi
PROMPT_ERR=$(mktemp)
# Each template is rendered with EXACTLY the variables it declares -- prompt.py rejects extras,
# which is what makes a rename that updates only one side fail instead of rendering half a
# prompt. Positional args, not a word-split string, so a path with a space survives.
set -- render "$DISPATCH_TEMPLATE" --var "RUN_ROOT=$RUN_ROOT"
[ "$DISPATCH_TEMPLATE" = dispatch.headless ] && set -- "$@" --var "SKILL_DIR=$SKILL_DIR" --var "LANES=$LANES"
DISPATCH_RULE=$(python3 "$PROMPTS" "$@" 2>"$PROMPT_ERR") || {
    echo "agy_host: dispatch prompt failed to render:" >&2; cat "$PROMPT_ERR" >&2; exit 70; }
PROMPT=$(python3 "$PROMPTS" render manager \
    --var "RUN_ROOT=$RUN_ROOT" --var "SKILL_DIR=$SKILL_DIR" --var "LANES=$LANES" \
    --var "DISPATCH_RULE=$DISPATCH_RULE" 2>"$PROMPT_ERR") || {
    echo "agy_host: manager prompt failed to render:" >&2; cat "$PROMPT_ERR" >&2; exit 70; }
rm -f "$PROMPT_ERR"

case "$MODE" in
    print)
        printf '%s\n' "$PROMPT"
        ;;
    headless)
        command -v agy >/dev/null 2>&1 || { echo "agy not installed" >&2; exit 69; }
        # Manager defaults to the deepest-reasoning model at high effort (the manager
        # gates and merges everything — reasoning quality dominates its cost);
        # override with AGY_HOST_MODEL / AGY_HOST_EFFORT (`agy models` lists slugs).
        set -- -p "$PROMPT" --output-format json --print-timeout "${AGY_HOST_PRINT_TIMEOUT:-60m}" \
               --model "${AGY_HOST_MODEL:-gemini-3.1-pro-high}" --effort "${AGY_HOST_EFFORT:-high}"
        [ "$SKIP_PERMS" = 1 ] && set -- "$@" --dangerously-skip-permissions
        # Outer wall-clock timeout: no harness is trusted to stop itself (SKILL.md §10).
        # NOT exec: a headless run whose tools were auto-denied still exits 0 with
        # status SUCCESS and an empty response (agy 1.2.6, observed live), so exec'ing
        # would hand the caller that 0 as if the manager had done the work. Capture the
        # envelope, show it, and put it through the same denial check adapters.py
        # applies to every lane (SKILL.md §10, "headless green can hide denials").
        ENV_FILE=${AGY_HOST_ENVELOPE:-$(mktemp)}
        timeout "${AGY_HOST_TIMEOUT:-4h}" agy "$@" >"$ENV_FILE" 2>&1
        RC=$?
        cat "$ENV_FILE"
        if ! python3 "$SKILL_DIR/scripts/adapters.py" denials "$ENV_FILE"; then
            echo "agy_host: manager run rejected — see the denial lines above; envelope kept at $ENV_FILE" >&2
            [ "$SKIP_PERMS" = 1 ] || echo "agy_host: headless auto-denies tools it cannot prompt for; re-run with --yolo, or add the allow-rule the notice names to settings.json" >&2
            [ "$RC" = 0 ] && RC=3
        fi
        exit "$RC"
        ;;
    session)
        command -v agy >/dev/null 2>&1 || { echo "agy not installed" >&2; exit 69; }
        # Held stream-json session: the process outlives each turn, so native subagent
        # lanes survive their dispatch and agy_session.py polls until every antigravity
        # lane in $LANES has written .devloop/native/report-<id>.json. Same denial check
        # as the single-shot path -- a held session can be auto-denied just as quietly.
        PROMPT_FILE=$(mktemp)
        printf '%s\n' "$PROMPT" > "$PROMPT_FILE"
        ENV_FILE=${AGY_HOST_ENVELOPE:-$(mktemp)}
        EVENTS_FILE=${AGY_HOST_EVENTS:-$RUN_ROOT/.devloop/native/session-events.ndjson}
        mkdir -p "$(dirname "$EVENTS_FILE")"
        # The poll predicate is receipt-backed only when it is GIVEN a jobs root. --jobs-root
        # existed on agy_session.py from the day it was added and no caller ever passed it, so
        # every AGY run kept using the agent-writable report-<id>.json it was built to replace.
        JOBS_ROOT=${AGY_HOST_JOBS_ROOT:-$RUN_ROOT/.devloop/jobs}
        mkdir -p "$JOBS_ROOT"
        set -- --prompt-file "$PROMPT_FILE" --lanes "$LANES" --run-root "$RUN_ROOT" \
               --envelope-out "$ENV_FILE" --events-out "$EVENTS_FILE" \
               --jobs-root "$JOBS_ROOT" \
               --model "${AGY_HOST_MODEL:-gemini-3.1-pro-high}" \
               --effort "${AGY_HOST_EFFORT:-high}" \
               --poll-max "${AGY_HOST_POLL_MAX:-8}"
        [ "$SKIP_PERMS" = 1 ] && set -- "$@" --yolo
        # A run marker, so a monitor can tell "quiet because it is thinking" from "finished".
        # Staleness alone calls a manager inside a long run_command dead (measured: 128s silent).
        STATUS_FILE=$(dirname "$EVENTS_FILE")/session.status
        printf '{"state":"running","pid":%s,"events":"%s","started_at":%s}\n' "$$" "$EVENTS_FILE" "$(date +%s)" > "$STATUS_FILE"
        trap 'printf "{\"state\":\"finished\"}\n" > "$STATUS_FILE"' EXIT INT TERM
        if [ "$USE_TMUX" = 1 ] && command -v tmux >/dev/null 2>&1; then
            # A manager with no panes is a manager you cannot watch. devloop.sh has had a tmux
            # grid since the beginning (devloop.sh:52); the AGY path never used it, so an
            # operator's only signal was the envelope, at the end. Pane 0 runs the manager,
            # pane 1 tails the SAME event stream through agy_monitor.py.
            TSESS=${AGY_HOST_TMUX_SESSION:-devloop-agy-$$}
            tmux new-session -d -s "$TSESS" -c "$RUN_ROOT" \
                "timeout ${AGY_HOST_TIMEOUT:-4h} python3 '$SKILL_DIR/scripts/agy_session.py' $(for x in "$@"; do printf "'%s' " "$x"; done); echo; echo '[manager exited rc='\$?']'; exec sh"
            tmux split-window -t "$TSESS:0" -c "$RUN_ROOT" \
                "python3 '$SKILL_DIR/scripts/agy_monitor.py' '$EVENTS_FILE' --follow; exec sh"
            tmux select-layout -t "$TSESS:0" even-horizontal >/dev/null 2>&1 || true
            echo "agy_host: manager running in tmux session '$TSESS' (attach: tmux attach -t $TSESS)"
            echo "agy_host: event stream $EVENTS_FILE"
            echo "agy_host: status snapshot: python3 $SKILL_DIR/scripts/agy_monitor.py $EVENTS_FILE --once"
            # Wait for the manager pane so this script's exit still means what it meant before.
            while tmux has-session -t "$TSESS" 2>/dev/null && [ "$(tmux list-panes -t "$TSESS:0" -F 1 2>/dev/null | wc -l)" -gt 0 ]; do
                [ -s "$ENV_FILE" ] && break
                sleep 5
            done
            # agy_session.py writes its exit code here before returning, because under tmux
            # its real status is otherwise unrecoverable: this branch used to set RC=0 and
            # downgrade only on a missing envelope, which silently turned exit 5 (poll budget
            # spent, lanes still unreported) into success -- the envelope is written BEFORE
            # that return. Measured 2026-09-19.
            RC_FILE=$(dirname "$EVENTS_FILE")/session.rc
            if [ -s "$RC_FILE" ]; then
                RC=$(cat "$RC_FILE")
            else
                RC=3   # no recorded status at all: the session did not reach its own exit
            fi
        else
            [ "$USE_TMUX" = 1 ] && echo "agy_host: tmux not found; running without panes" >&2
            timeout "${AGY_HOST_TIMEOUT:-4h}" python3 "$SKILL_DIR/scripts/agy_session.py" "$@"
            RC=$?
        fi
        rm -f "$PROMPT_FILE"
        # DEFAULT, not opt-in: a run with a transcript gets a UI element for it. The stream is
        # NDJSON in a scratch directory, which nothing will ever open; the rendered page is what
        # an operator (or a client) actually shows for the task. Rendered from the same State
        # the pane and the JSON report use, so the three cannot disagree.
        TRANSCRIPT=$(dirname "$EVENTS_FILE")/transcript.html
        REPORT_JSON=$(dirname "$EVENTS_FILE")/monitor-report.json
        TASKS_JSON=$(dirname "$EVENTS_FILE")/tasks.json
        python3 "$SKILL_DIR/scripts/agy_monitor.py" "$EVENTS_FILE" --once \
            --report-out "$REPORT_JSON" --html "$TRANSCRIPT" \
            --tasks-out "$TASKS_JSON" --lanes "$LANES" >/dev/null 2>&1
        [ -s "$TASKS_JSON" ] && echo "agy_host: task records $TASKS_JSON (mirror into the host's native task list)"
        [ -s "$TRANSCRIPT" ] && echo "agy_host: transcript $TRANSCRIPT"
        [ -s "$REPORT_JSON" ] && echo "agy_host: monitor report $REPORT_JSON"

        if [ -s "$ENV_FILE" ] && ! python3 "$SKILL_DIR/scripts/adapters.py" denials "$ENV_FILE"; then
            echo "agy_host: manager session rejected — see the denial lines above; envelope kept at $ENV_FILE" >&2
            [ "$SKIP_PERMS" = 1 ] || echo "agy_host: headless auto-denies tools it cannot prompt for; re-run with --yolo, or add the allow-rule the notice names to settings.json" >&2
            [ "$RC" = 0 ] && RC=3
        fi
        exit "$RC"
        ;;
    interactive)
        command -v agy >/dev/null 2>&1 || { echo "agy not installed" >&2; exit 69; }
        echo "Starting interactive agy. Paste the manager prompt below (or run /dev-loop lanes:$LANES):"
        echo "--------------------------------------------------------------------------"
        printf '%s\n' "$PROMPT"
        echo "--------------------------------------------------------------------------"
        exec agy
        ;;
esac

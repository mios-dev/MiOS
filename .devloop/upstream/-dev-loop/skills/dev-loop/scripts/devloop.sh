#!/usr/bin/env sh
# Dev Loop orchestrator — POSIX sh + git + python3 (tmux optional).
#
#   devloop.sh <lanes.json> [--layout auto|tmux_grid|detached|headless] [--dry-run] [--keep] [--check]
#
# Any harness can invoke this from its shell tool; lanes may run in any harness (lane.worker.harness).
# Per lane, in dependency order: worktree → launch (adapters.py run) → wait → ownership audit →
# two-sided gate → full gate → secrets scan → explicit-path commit → merge --no-ff (abort on conflict,
# keep worktree). Exit 0 all merged; 1 lane failed/partial; 2 VACUOUS lane (never merged); 64 usage.
set -eu
export CI=1 GIT_TERMINAL_PROMPT=0 GIT_PAGER=cat PAGER=cat NO_COLOR=1
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd); AD="$SKILL_DIR/scripts/adapters.py"; PY=${PYTHON:-python3}
JOB_PY="$SKILL_DIR/scripts/job.py"   # turn-durable work: setsid + a shell-written receipt
command -v "$PY" >/dev/null 2>&1 || { echo "python3 required" >&2; exit 64; }

if [ "${1:-}" = "--check" ]; then
  for b in git "$PY" tmux claude codex gemini agy gitleaks; do printf '%-9s %s\n' "$b" "$(command -v "$b" 2>/dev/null || echo '-')"; done
  "$PY" -c 'import jsonschema' 2>/dev/null && echo "jsonschema ok" || echo "jsonschema missing (structural validation only)"; exit 0
fi
LANES=${1:?usage: devloop.sh <lanes.json> [--layout L] [--dry-run] [--keep] [--check]}; shift
DRY=0; KEEP=0; LAYOUT=auto; CONCURRENT=0
while [ $# -gt 0 ]; do case "$1" in
  --dry-run) DRY=1;; --keep) KEEP=1;; --layout) LAYOUT=$2; shift;; --no-tmux) LAYOUT=detached;;
  --concurrent) CONCURRENT=1;;
  *) echo "unknown flag $1" >&2; exit 64;; esac; shift; done

ROOT=$(git rev-parse --show-toplevel) || { echo "not in a git repo" >&2; exit 64; }
cd "$ROOT"
RUN="$ROOT/.devloop/run-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$RUN"
# Job state lives under the run dir, so it is excluded with it and audited with it.
JOBS="$RUN/jobs"; mkdir -p "$JOBS"
SPEC="$RUN/lanes.normalized.json"
"$PY" "$AD" validate "$LANES" --out "$SPEC" || exit 64
field() { "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); v=d
for k in sys.argv[2].split("."): v=v.get(k,"") if isinstance(v,dict) else ""
print(v if not isinstance(v,(list,dict)) else json.dumps(v))' "$1" "$2"; }
BASE=$(field "$SPEC" base_ref); WT_ROOT=$(field "$SPEC" worktree_root); INTEG=$(field "$SPEC" integration_cmd)
[ "$LAYOUT" = auto ] && LAYOUT=$(field "$SPEC" terminal_layout); [ "$LAYOUT" = auto ] || [ -z "$LAYOUT" ] && LAYOUT=tmux_grid
[ "$LAYOUT" = tmux_grid ] && ! command -v tmux >/dev/null 2>&1 && { echo "tmux not found; using detached"; LAYOUT=detached; }
[ "$LAYOUT" = wt_grid ] && LAYOUT=detached
if [ -f .git/info/exclude ]; then
  sed -i '/^\.devloop\/\?$/d' .git/info/exclude 2>/dev/null || true
fi
for e in ".devloop/run-*/" "$WT_ROOT/"; do grep -qxF "$e" .git/info/exclude 2>/dev/null || echo "$e" >> .git/info/exclude; done
[ -z "$(git status --porcelain)" ] || { echo "refusing: base tree is dirty" >&2; exit 64; }
BASE_SNAP="$RUN/base-tree-before.json"
"$PY" "$AD" base-audit --root "$ROOT" --save "$BASE_SNAP"
SESSION="devloop-$(basename "$RUN")"; STATUS=0

launch() { # $1=id  — provision worktree + start worker per layout
  ID=$1; LJ="$RUN/lane-$ID.json"; "$PY" "$AD" lane "$SPEC" "$ID" --out "$LJ" >/dev/null
  WT=$(field "$LJ" worktree); [ -n "$WT" ] || WT="$WT_ROOT/$ID"; WTA="$ROOT/$WT"; BR="lane/$ID"
  echo "== lane $ID [$(field "$LJ" worker.harness)] -> $WT ($BR from $BASE)"
  [ "$DRY" = 1 ] && return 0
  if [ -d "$WTA" ]; then
    echo "  worktree exists; cleaning and reusing"
    git -C "$WTA" checkout -f "$BR" 2>/dev/null || git -C "$WTA" checkout -f -B "$BR" "$BASE"
    git -C "$WTA" reset --hard "$BR" 2>/dev/null || git -C "$WTA" reset --hard "$BASE" 2>/dev/null || true
    git -C "$WTA" clean -ffd
  elif git show-ref --verify --quiet "refs/heads/$BR"; then "$PY" "$AD" git --wt "$ROOT" -- worktree add --quiet "$WT" "$BR";
  else "$PY" "$AD" git --wt "$ROOT" -- worktree add --quiet "$WT" -b "$BR" "$BASE"; fi
  CMD="$PY '$AD' run --lane '$LJ' --wt '$WTA' --report '$RUN/report-$ID.json' --log '$RUN/worker-$ID.log' --skill '$SKILL_DIR/SKILL.md'; echo \$? > '$RUN/worker-$ID.exit'"
  case "$LAYOUT" in
    headless)
      # SEQUENTIAL by design: one lane at a time, in the foreground. Kept for the case where
      # you want deterministic ordering or a single lane; everything else should fan out.
      if [ "${CONCURRENT:-0}" = 1 ] || [ "${DEVLOOP_CONCURRENT:-0}" = 1 ]; then
        BUDGET=$(field "$LJ" worker.timeout_s); case "$BUDGET" in ''|*[!0-9]*) BUDGET=1800;; esac
        if ! "$PY" "$JOB_PY" spawn --root "$JOBS" --id "$ID" --cwd "$WTA" \
               --budget "$BUDGET" --label "lane $ID" -- sh -c "$CMD" >/dev/null; then
          echo "  $ID: SPAWN FAILED -- lane never started" >&2
          echo "125" > "$RUN/worker-$ID.exit"
        fi
      else
        sh -c "$CMD" || true
      fi;;
    tmux_grid)
      if tmux has-session -t "$SESSION" 2>/dev/null; then tmux split-window -t "$SESSION:0" -c "$WTA" "$CMD; exec sh"; tmux select-layout -t "$SESSION:0" tiled
      else tmux new-session -d -s "$SESSION" -c "$WTA" "$CMD; exec sh"; fi;;
    *)
      # DETACHED lanes are spawned as JOBS, not as `( ... ) &`. A plain background child is
      # still a child: it dies when the shell's session ends, which is precisely the turn
      # boundary that has killed lane trees here before. job.py spawns under setsid with stdin
      # closed, so the lane is an orphan by construction and its completion is a receipt the
      # SHELL writes, never a file the model is asked to create.
      # field() prints "" and exits 0 for a missing key, so `$(field … || echo 1800)` could
      # never fire -- it read as a default and was dead code. Guard on the VALUE instead.
      BUDGET=$(field "$LJ" worker.timeout_s); case "$BUDGET" in ''|*[!0-9]*) BUDGET=1800;; esac
      # A spawn that fails must not be swallowed: with no job directory, reap_lane silently
      # falls back to the old unbounded `.exit` wait -- the exact hang job.py replaced.
      if ! "$PY" "$JOB_PY" spawn --root "$JOBS" --id "$ID" --cwd "$WTA" \
             --budget "$BUDGET" --label "lane $ID" -- sh -c "$CMD" >/dev/null; then
        echo "  $ID: SPAWN FAILED -- lane never started" >&2
        echo "125" > "$RUN/worker-$ID.exit"
      fi;;
  esac
}

# Wait for a whole WAVE on ONE deadline, then reap each lane.
#
# Two defects lived in the previous shape. (1) `job.py wait` was called unguarded under
# `set -eu`, and wait exits 2 when a lane is not done rc 0 and 3 when it is lost -- so a lane
# that outran its job budget KILLED THE ORCHESTRATOR at the wait, before any gate, before the
# run status file, before the ledger, and the run exited 2, which in this script's own contract
# means "vacuous lane". Measured 2026-09-19. A non-zero wait is the normal reporting channel
# here, not an error, so it must be swallowed and read from the state instead.
# (2) Waiting lane-by-lane multiplied the budget by the number of lanes: each wait started only
# after the previous one returned, so N lanes could consume N x LANE_WAIT_BUDGET. job.py wait
# already takes repeated --id under a single deadline.
wait_wave() {
  IDS=''
  for ID in "$@"; do [ -d "$JOBS/$ID" ] && IDS="$IDS --id $ID"; done
  [ -n "$IDS" ] || return 0
  # shellcheck disable=SC2086
  "$PY" "$JOB_PY" wait --root "$JOBS" $IDS --budget "${LANE_WAIT_BUDGET:-5400}" --interval "${LANE_WAIT_INTERVAL:-2}" || :
}

# Turn a lane's terminal state into the exit file the gate reads. The `.exit` fallback covers
# tmux and headless lanes, which are children of a shell that is still alive by construction.
reap_lane() {
  ID=$1
  if [ -d "$JOBS/$ID" ]; then
    ST=$("$PY" "$JOB_PY" status --root "$JOBS" --id "$ID" --json 2>/dev/null | sed -n 's/.*"state": *"\([a-z]*\)".*/\1/p' | head -1)
    case "$ST" in
      lost|forged)
        echo "  $ID job $ST -- no receipt; treating as failed (worker died without reporting)"
        echo "125" > "$RUN/worker-$ID.exit";;
      running)
        # The wave budget is spent and the lane is STILL ALIVE inside its worktree. Gating here
        # would audit, stage and merge a tree a running agent is still writing to. Kill it
        # first; the wrapper's TERM trap writes a real receipt, so no code is invented.
        echo "  $ID over the wave budget -- terminating it before gating" >&2
        "$PY" "$JOB_PY" kill --root "$JOBS" --id "$ID" --signal TERM >/dev/null 2>&1 || :
        W=0
        while [ "$W" -lt "${REAP_GRACE_S:-30}" ] && [ "$("$PY" "$JOB_PY" status --root "$JOBS" --id "$ID" --json 2>/dev/null | sed -n 's/.*"state": *"\([a-z]*\)".*/\1/p' | head -1)" = running ]; do
          sleep 5; W=$((W+5))
        done
        "$PY" "$JOB_PY" kill --root "$JOBS" --id "$ID" --signal KILL >/dev/null 2>&1 || :
        sleep 2
        [ -f "$JOBS/$ID/exit" ] && cp "$JOBS/$ID/exit" "$RUN/worker-$ID.exit" || echo "124" > "$RUN/worker-$ID.exit";;
      *) [ -f "$JOBS/$ID/exit" ] && cp "$JOBS/$ID/exit" "$RUN/worker-$ID.exit";;
    esac
    [ -f "$JOBS/$ID/out" ] && cat "$JOBS/$ID/out" >> "$RUN/worker-$ID.log" 2>/dev/null
    [ -f "$JOBS/$ID/err" ] && cat "$JOBS/$ID/err" >> "$RUN/worker-$ID.log" 2>/dev/null
  elif [ ! -f "$RUN/worker-$ID.exit" ]; then
    # No job and no receipt: a tmux or headless lane that never wrote one. Not success.
    echo "  $ID: no job and no receipt -- treating as failed"
    echo "125" > "$RUN/worker-$ID.exit"
  fi
  echo "  $ID worker exit=$(cat "$RUN/worker-$ID.exit" 2>/dev/null || echo '?')"
}

gate_merge() { # $1=id — audit, gate, commit, merge. Sets STATUS.
  ID=$1; LJ="$RUN/lane-$ID.json"; WT=$(field "$LJ" worktree); [ -n "$WT" ] || WT="$WT_ROOT/$ID"; WTA="$ROOT/$WT"; BR="lane/$ID"; REP="$RUN/report-$ID.json"
  echo "== gate $ID"
  [ -f "$REP" ] || { echo "  NO REPORT — parking diff"; git -C "$WTA" diff > "$RUN/lane-$ID.patch"; STATUS=1; return; }
  RS=$(field "$REP" status); echo "  report status=$RS"
  "$PY" "$AD" owned --lane "$LJ" --wt "$WTA" || { git -C "$WTA" diff > "$RUN/lane-$ID.patch"; STATUS=1; return; }
  "$PY" "$AD" gate --lane "$LJ" --wt "$WTA" --run "$RUN" --root "$ROOT"; rc=$?
  [ $rc -eq 0 ] || { [ $rc -eq 2 ] && STATUS=2 || [ "$STATUS" = 2 ] || STATUS=1; return; }
  [ "$RS" = done ] || { echo "  gates hold but the lane says '$RS' — not merging; read $REP"; [ "$STATUS" = 2 ] || STATUS=1; return; }
  field "$LJ" owned_paths | "$PY" -c 'import json,sys; print("\n".join(json.load(sys.stdin)))' | while IFS= read -r p; do git -C "$WTA" add -- "$p" 2>/dev/null || true; done
  [ -n "$(git -C "$WTA" diff --cached --name-only)" ] || { echo "  nothing staged — lane produced no change"; return; }
  "$PY" "$AD" secrets --wt "$WTA" || { git -C "$WTA" reset -q; [ "$STATUS" = 2 ] || STATUS=1; return; }
  "$PY" "$AD" deps --wt "$WTA" || { git -C "$WTA" reset -q; [ "$STATUS" = 2 ] || STATUS=1; return; }
  TID=$(field "$LJ" task_id); TRAILER=""; [ -n "$TID" ] && TRAILER="Task-Id: $TID"
  git -C "$WTA" commit --quiet -m "lane($ID): $(field "$LJ" objective | head -c 60)" -m "$(field "$REP" summary | head -c 600)" \
    -m "Verified: positive=$(field "$LJ" positive_cmd) ; negative=$(field "$LJ" negative_control_cmd) (named: $(field "$LJ" negative_expect))" ${TRAILER:+-m "$TRAILER"}
  if ! "$PY" "$AD" base-audit --root "$ROOT" --before "$BASE_SNAP" --lanes "$SPEC"; then
    echo "  BASE TREE LEAKAGE DETECTED before merge — halting" >&2
    [ "$STATUS" = 2 ] || STATUS=1
    return
  fi
  if "$PY" "$AD" git --wt "$ROOT" -- merge --no-ff --no-edit "$BR" >/dev/null; then echo "  merged $BR"
    [ "$KEEP" = 1 ] || { git worktree remove --force "$WT"; git branch -D "$BR" >/dev/null; }
    if [ -n "$TID" ] && [ -f "$ROOT/.devloop/tasks.jsonl" ]; then
      "$PY" "$SKILL_DIR/scripts/artifacts.py" tasks set "$TID" done --evidence "lane $ID merged $(git rev-parse --short HEAD); see $RUN/report-$ID.json" --root "$ROOT" >/dev/null \
        && "$PY" "$SKILL_DIR/scripts/artifacts.py" tasks render --root "$ROOT" >/dev/null && git add -- .devloop/tasks.jsonl TASKS.md && git commit -q -m "chore(tasks): $TID done" -m "Task-Id: $TID" || echo "  (task ledger update skipped)"
    fi
  else git merge --abort 2>/dev/null || true; echo "  MERGE CONFLICT — aborted; worktree and branch kept for review" >&2; [ "$STATUS" = 2 ] || STATUS=1; fi
}

# Waves: every lane whose depends_on are all merged runs in parallel; then gate+merge; next wave.
# Materialised to a file rather than piped. A pipeline put the loop body in a SUBSHELL (so
# STATUS never reached the parent) and hid two failures: `waves` exiting non-zero, and `waves`
# printing nothing. Both left the loop with zero iterations and the run exiting 0 -- an
# Empty-Set Pass in which no lane ran at all. Reading from fd 3 keeps the body's stdin free,
# so a foreground worker cannot eat the wave list.
"$PY" "$AD" waves "$SPEC" > "$RUN/waves.txt" || { echo "waves failed" >&2; exit 64; }
[ -s "$RUN/waves.txt" ] || { echo "no waves: $(basename "$LANES") yielded no runnable lane" >&2; exit 2; }
while IFS= read -r WAVE <&3; do
  # Throttle the fan-out. Every agy lane shares ONE cached credential in the keyring, and the
  # references note that parallel lanes without a live keyring each re-ask for auth and hang
  # their budget away -- so an unbounded wave is not free. The cap is provisional: no
  # measurement here establishes the right number, so it is conservative and overridable
  # rather than tuned. MAX_CONCURRENT=0 disables the throttle.
  for id in $WAVE; do
    if [ "${MAX_CONCURRENT:-4}" -gt 0 ]; then
      while [ "$("$PY" "$JOB_PY" status --root "$JOBS" 2>/dev/null | grep -c ' running ')" -ge "${MAX_CONCURRENT:-4}" ]; do
        sleep 5
      done
    fi
    launch "$id"
  done
  [ "$DRY" = 1 ] && continue
  # shellcheck disable=SC2086
  wait_wave $WAVE
  for id in $WAVE; do reap_lane "$id"; done
  for id in $WAVE; do gate_merge "$id"; done
  echo "$STATUS" > "$RUN/status"
done 3< "$RUN/waves.txt"
[ "$DRY" = 1 ] && { echo "dry run complete"; exit 0; }
[ -n "$INTEG" ] && [ "$STATUS" = 0 ] && { echo "== integration: $INTEG"; sh -c "$INTEG" || { echo "  integration FAILED on base"; STATUS=1; }; }
git worktree prune
"$PY" "$AD" ledger --root "$ROOT" --status "run-exit-$STATUS" --objective "$(field "$SPEC" objective)" --done "$(ls "$RUN"/report-*.json 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ')" --next "read $RUN/report-*.json; re-plan non-done lanes" >/dev/null 2>&1 && git add -- .devloop/LEDGER.md 2>/dev/null && git commit -q -m "chore(devloop): ledger entry (run exit $STATUS)" 2>/dev/null || true
echo "== run artefacts: $RUN ; exit $STATUS"; exit $STATUS

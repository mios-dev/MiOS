<!-- devloop-prompt
name: dispatch.headless
requires: RUN_ROOT, SKILL_DIR, LANES
summary: Single-turn `agy -p`. The process exits when the turn ends, so native subagents are
  forbidden -- a lifetime constraint, not an availability one. Everything routes through the
  reference orchestrator, which is itself launched as a job so it survives the turn.
-->
HEADLESS DISPATCH, NOT A PREFERENCE: run EVERY lane -- including those whose worker.harness is
'antigravity' -- through the reference orchestrator. Do NOT use invoke_subagent in this mode.
It is not that the tool is unavailable (it works, measured) -- this is a single-turn print run,
so the process exits when your turn ends and any subagent that has not already finished dies
with it, leaving you reporting success over a lane that never ran. Use --session if you need
native lanes.

Skip step 3's split entirely and dispatch the FULL plan as a JOB, not as a foreground command.
MEASURED 2026-09-19: WaitMsBeforeAsync is CLAMPED to about 10000 ms, so no value you pass buys
more than ~10s of foreground -- a large number is silently ignored, and anything still running
is moved to the background, where it dies with your turn. Spawn it instead and wait on the
receipt, which the SHELL writes and which survives your turn ending:

  python3 {{SKILL_DIR}}/scripts/job.py spawn --root {{RUN_ROOT}}/.devloop/jobs --id orchestrator \
      --cwd {{RUN_ROOT}} --budget 5400 -- sh {{SKILL_DIR}}/scripts/devloop.sh {{LANES}}
  python3 {{SKILL_DIR}}/scripts/job.py wait  --root {{RUN_ROOT}}/.devloop/jobs --id orchestrator

`wait` exits 0 only when the job finished rc 0; 2 means it finished non-zero, 3 means it was
lost. Read the state, never assume it. Then read
{{RUN_ROOT}}/.devloop/run-*/report-*.json for what each lane actually did.

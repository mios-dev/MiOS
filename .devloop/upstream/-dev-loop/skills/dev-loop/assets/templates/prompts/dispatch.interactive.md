<!-- devloop-prompt
name: dispatch.interactive
requires: RUN_ROOT
summary: Interactive session. A person is waiting, so the process lives as long as the run.
-->
YOUR NATIVE MULTI-AGENT MACHINERY IS THE DEFAULT for your own lanes.

Run every lane whose worker.harness is 'antigravity' as a native Antigravity subagent
(invoke_subagent with workspace: branch, one subagent per lane, the lane's contract -- id,
objective, owned_paths, both control commands, budget -- as its prompt). Dispatch every
independent lane at once, then wait for them; they are concurrent by design. Collect each
native lane's devloop_report into {{RUN_ROOT}}/.devloop/native/report-LANE_ID.json (use
write_file). You are interactive, so you can wait for each subagent to finish.

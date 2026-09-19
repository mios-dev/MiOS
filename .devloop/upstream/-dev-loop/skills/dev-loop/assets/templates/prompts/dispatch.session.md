<!-- devloop-prompt
name: dispatch.session
requires: RUN_ROOT
summary: Held stream-json session. The process outlives each turn, so native subagent lanes
  survive their dispatch and the host sends follow-up turns until every lane has reported.
-->
HELD SESSION: your process stays alive across turns, so YOUR NATIVE MULTI-AGENT MACHINERY IS
THE DEFAULT for your own lanes.

Run every lane whose worker.harness is 'antigravity' as a native Antigravity subagent
(invoke_subagent with workspace: branch, one subagent per lane, the lane's contract -- id,
objective, owned_paths, both control commands, budget -- as its prompt). Dispatch every
independent lane in the SAME turn; they run concurrently and serialising them only wastes the
run. Collect each native lane's devloop_report into
{{RUN_ROOT}}/.devloop/native/report-LANE_ID.json (use write_file).

Ending a turn does NOT end the run. If a subagent has not finished, say so plainly and end the
turn -- the host will send you a follow-up turn to continue waiting. NEVER write a report file
for a lane that has not actually reported, and never claim a lane finished because you
dispatched it.

Keep ALL per-lane scratch you create -- lane contracts, parked patches, notes -- inside
{{RUN_ROOT}}/.devloop/native/ next to the reports. Do NOT write scratch at
{{RUN_ROOT}}/.devloop/ top level: that is tracked space holding the lane plan, the ledger and
the lanes' findings, and files dropped there become part of the repository's state.

<!-- AI-hint: Round-2 MINOR task list for Antigravity/Gemini (Gemini 3.2 Pro, High). Small, self-contained verification/polish/docs/install-residual tasks chosen to be DISJOINT from (a) Claude's concurrent agent-system work and (b) the in-flight open-agent-federation research -- so the overall roadmap is NOT disrupted. Follows MIOS-GEMINI-TASKS-2026-06-22.md (Round 1, done).
     AI-related: ./MIOS-GEMINI-TASKS-2026-06-22.md, ./MIOS-ROADMAP-2026-06-22.md, ./install-robustness-2026-06-21.md, ../../../../tools/generate-pod-quadlets.py -->
# MiOS — Gemini (Antigravity) task list — Round 2 (minor, 2026-06-22)

Round 1 (`MIOS-GEMINI-TASKS-2026-06-22.md`) is done. These are **minor, low-risk,
self-contained** follow-ups. They must **NOT disrupt the roadmap** — so they are
scoped clear of the two active workstreams below.

## ⛔ DO NOT TOUCH (active elsewhere — would disrupt the roadmap)

- `usr/lib/mios/agent-pipe/server.py`, `usr/share/mios/mios.toml` sections `[agents.*]` /
  `[agents._defaults]` / `[nodes.*]` / `[ai]` / `[cost]`, `usr/libexec/mios/opencode-gateway/`,
  `hermes-worker.service`, `automation/38-drift-checks.sh`, the OWUI firstboot wiring — **Claude's**.
- The **agent federation / A2A / MCP surfaces** — the A2A card/`agent.json`, `agent-passport`,
  `a2a-peers.json`, `/a2a`, MCP, anything about agent registration / discovery / credentials /
  council membership — **reserved for the open-agent-federation research + Claude's follow-up**.
  (A standards-based open-federation redesign is in flight; editing these now would collide.)

**Gemini owns (Round 2):** the quadlets you just edited (`usr/share/containers/systemd/*`),
`tools/generate-pod-quadlets.py`, `usr/share/doc/mios/**` docs, `C:\mios-bootstrap\*` install
scripts (except agent/federation), the AI-header tags.

---

## G2-TASK 1 — Verify + clean up the Round-1 pod quadlets (highest value) [DONE]
*Why: Round 1 added `Pod=` to many `.container` files via bulk edits; verify they're correct + catch any artifact.*
- Run `python3 tools/generate-pod-quadlets.py --check` → must report **no drift** for all 7 pods. Fix any drift.
- **Comment-artifact sweep:** a bulk replace can insert a `Pod=…` line into the WRONG place (observed in `mios-llm-heavy-alt.container` ~line 89, where `Pod=mios-ai-heavy.pod` landed *inside a comment block* under a `# [Container]` reference, breaking the comment + creating a stray directive). `grep -nE '^Pod=' usr/share/containers/systemd/*.container` and confirm **each is the FIRST line under the real `[Container]` header**, exactly once per member, and NOT inside a comment. Fix any stray/duplicate.
- Confirm Law 6 still holds: every podded `.container` keeps its `User=`/`Group=`/`Delegate=` (the documented root exceptions intact), and `bootc container lint`-relevant structure is valid.
- **Accept:** `--check` green; exactly one well-placed `Pod=` per member; no mangled comments; the un-gated pods would render + start.

## G2-TASK 2 — Pod architecture concept doc [DONE]
- Write `usr/share/doc/mios/concepts/pod-architecture-2026-06-22.md`: the 7-pod map (members + rationale), the port-minimization (~24 raw binds → ~8 front doors), the **host-services-stay-host** constraint (hermes-agent/agent-pipe/mcp/etc. reached via `host.containers.internal`), the SSOT pod-gen lifecycle, and the standalone exceptions (OWUI front door, searxng). Cite `MIOS-ROADMAP-2026-06-22.md` §WS-C.
- **Accept:** doc committed with the AI-hint/AI-related header; matches the live `[pods.*]` SSOT.

## G2-TASK 3 — Install-robustness MED residual (mios-bootstrap + docs) [DONE]
From `usr/share/mios/docs/install-robustness-2026-06-21.md` "Med:" list — each is small + self-contained:
- `.wslconfig` written BOM-free (verify it's done; the BOM voids `[wsl2]`).
- `mios-gui-watch.ps1`: add a single-instance mutex (`Global\MiOS-GuiWatch`) to the unbounded poll.
- `identity.env.example`: dead vs the `mios.toml` SSOT — delete it or make the installer source it (don't double-track).
- `CLAUDE.md` model table drift vs `mios.toml [ai]` — update the doc table to match the SSOT (edit the DOC, never `[ai]`).
- `seed-merge`: drop the dead `ROOT_FILES` references to missing files.
- `bootstrap.sh`: add `curl --retry` on the canonical fetch (mirror the PS-side 3× backoff).
- `install-host-tools.ps1`: hard `throw` on a winget pkg failure → warn + retry/checksum + per-pkg exit.
- **Accept:** each item fixed in its own file; `[Parser]::ParseFile` clean on any `.ps1`; `bash -n` clean on `.sh`.

## G2-TASK 4 — AI-header tags on Round-1 new/changed files [DONE]
- Run/refresh the `# AI-hint:` / `# AI-related:` / `# AI-functions:` headers (the `mios-ai-tag` system) on the files Round 1 created/changed (the new `.pod` quadlets, any render script, the new docs) so the codebase index stays consistent. Don't tag generated/transient files.
- **Accept:** `mios-ai-hint-coverage` (the drift-gate) stays green; new files carry headers.

## Notes
- Commit to `main`, no branches; no hardcoded values that belong in the SSOT; Tailscale OFF.
- These are independent — do in any order; mark each DONE here + commit.
- If any task would require touching a ⛔ file/surface above, STOP and leave it — it's owned by the active agent-federation work.

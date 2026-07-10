<!-- AI-hint: Authoritative completion plan for ALL outstanding MiOS hardening/perfection tasks as of the 2026-06-15 session. Prioritized P0-P4, ownership-tagged (Claude / operator-decision / operator-action), status + concrete next step each. Longer-horizon multi-wave work lives in MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md; OS-control doctrine in research/ai-os-control-patterns-2026-06-15.md. -->

# MiOS Completion Plan — ALL outstanding tasks (refreshed 2026-06-15, end of session)

This is the single source of truth for what is DONE, what is OPEN, who owns it,
and the next concrete step. Companion docs:
- **research/ai-os-control-patterns-2026-06-15.md** — OS-control doctrine (the "how").
- **MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md** — the longer-horizon AIOS
  Wave 0–4 build (multi-agent execution; tracked separately, see §Roadmap).

Status legend: ✅ done+verified · 🟡 deployed/needs-operator-verify · 🔧 fixable-by-Claude on request · 🔑 needs-operator-decision · 👤 needs-operator-action · 🧱 larger/architecture.

---

## ✅ DONE + verified this session (2026-06-15)

**User-facing failures fixed**
- ✅ **Zen Smart Window identity + tool denial** — passthrough rewritten from a
  verbatim relay into a HYBRID loop: MiOS identity injected, MiOS verb surface
  merged with the browser tools, MiOS verbs executed server-side, only browser
  tool_calls returned to Zen, verbatim-relay fallback on error. Verified: "who are
  you?" → "I am MiOS AI … not a Mozilla/Smart Window product"; "list my windows" →
  ran `list_windows` server-side. (`server.py`, on `main` 4402b80.)
- 🟡 **Hermes desktop app (AppData\Local\hermes) launches** — root cause was the
  `windows-app-launch` skill (PowerShell path-guessing + curator-corrupted), NOT
  missing tools (the `mios` MCP is loaded: 113 tools, reachable at :8765). Rewrote
  the skill MCP-first, tightened the config `environment_hint`, pinned the skill.
  Verified the MiOS launcher resolves nautilus→flatpak, spotify/notepad→real UWP.
  **Operator-verify:** `/reset` a Hermes session, then "open nautilus". (Host-local
  — not in the repo; see caveat in §Risks.)

**OS-control + plane**
- ✅ **Windows OS-control executor restored** (:11437, logon task, firewall) — verified
  /health, `list_windows` = real host windows, agent reaches it via the WSL gateway.
- ✅ **Windows UIA semantic lane** — `/ui/find` + `/ui/click` + `windows_desktop_find_element_by_name`
  / `windows_desktop_click_element` (target controls by name, clickable centers).
- ✅ **Set-of-Marks grounding** — `/ui/list` + `windows_desktop_list_elements` (foreground
  controls as numbered marks).
- ✅ **os_control_health verb** — reports "control plane offline" instead of silent exit -1.
- ✅ **Host-recipe host-default** — host-describing recipes (show-network/disk-usage/…)
  default to the Windows host when interop exists (no more "describes the VM").
- ✅ **mios-find reorder** (real apps outrank shims; notepad→real app), **mios-powershell**
  exit-code + UTF-8-no-BOM, **disk-usage→JSON**, **service-status→structured**.

**AI plane**
- ✅ **Recall grounding** — dispatch-recall clean + native-loop anti-amnesia framing/fallback;
  **memory remember/recall→pgvector**; **filler-strip** ("this fact:" removed on store).
- ✅ **Model swap-thrash fix** (refine 45s→2.1s) + **VRAM incident recovery** (heavy lane
  stopped → granite 69s→8s).
- ✅ **web_extract** offline (miosfetch shadow removed) + tiered crawl4ai/CDP.

**Repo:** all of the above merged to **`main`** (no feature branch, per operator); branch deleted.

---

## OPEN — prioritized, with owner + next step

### P0 — decisions that gate responsiveness
1. **Heavy GPU lane policy** 🔑 — currently OFF (chat-responsive; nothing in the chat
   path uses :11441). **Decision:** keep off-by-default (recommended) vs on with a
   VRAM-budget/foreground-priority guard. → Durable next step (🔧, once decided):
   assert the off-default in `mios.toml` + a VRAM-pressure preflight before it starts.

### P1 — durability / SSOT
2. **Reconcile live drop-ins into source** 🔧 — confirm the runtime overrides survive a
   rebuild: `MIOS_DB_BACKEND=postgres` (verify `userenv.sh` maps `pgvector.db_backend`;
   live install.env was just stale) and any model-align (moot while heavy lane is off —
   revisit if re-enabled). Mostly folded into the pushed SSOT-lint work; verify end-to-end.
3. **Hermes desktop fix durability** 🔑/👤 — host-local edits (skill + config) can be
   reverted by a Hermes app reinstall/update. **Decision:** provision them from a
   Windows-side installer (e.g. C:\mios-bootstrap) so they persist, or accept host-local.

### P2 — OS-control perfection (research doc)
4. **Unify Windows shell contract** 🔧 — `mios-pwsh` shim (pwsh7→5.1 fall-through), re-point
   recipe `windows=` templates off the hardcoded 5.1 path, use `-File`, stage to per-agent %TEMP%.
5. **Finish launch-resolution hardening** 🔧 — App-Paths-first resolver returning target+method
   without launching; drop `es.exe` as load-bearing; Get-AppxPackage AUMID fallback.
   (Substantially covered by the mios-find reorder + launcher resolution; this is the last polish.)
6. **Sandbox the Linux bash path** 🔧🧱 — first-class jailed `run_bash` via bwrap+seccomp;
   Popen+setsid+killpg process-group timeout. (Non-urgent.)

### P3–P4 — depth
7. **Structured Linux discovery recipes** 🔧 — show-process/journal → JSON; fd/rg fallbacks.
8. **Web-research loop bounding** 🔧 — bound passes/time on hard news queries; return partial honestly.
9. **Wayland window-ops + sensitive-field guards** 🔧🔑 — local focus/move/resize via portal; a11y credential guards.
10. **Vision Set-of-Marks for non-UIA surfaces** 🔧🧱 — VLM-numbered-box grounding where UIA can't reach (the UIA lane already covers the common semantic case).
11. **Blind-path honesty flag** 🔧 — emit `unverified=true` on results when the executor is blind (os_control_health already reports the blind state).
12. **The generic `os_recipe` runner doesn't forward the `service` arg** 🔧 — dedicated `service_status` works; fix the generic dispatch-arg pass-through.

---

## 🔑 Operator policy calls (one line each unblocks the 🔧 work)
- **A. Heavy lane** — off-by-default (recommended) vs on-with-VRAM-policy?
- **B. UIA library** — keep built-in `System.Windows.Automation` (recommended; zero extra deps, already shipping) vs vendored FlaUI?
- **C. Executor auto-start** — start at firstboot vs operator-gated (current)?
- **D. rpm-ostree** — expose layering to an agent verb, or operator-only (recommended)?
- **E. Hermes desktop provisioning** — bake the MCP-first launch skill + hint into a Windows-side installer (durable) vs leave host-local?

---

## §Roadmap — longer-horizon (separate track)
The AIOS Wave 0–4 build (priority queue, per-child tool surfaces, eviction/preemption,
HITL replay, heavy-lane activation, federation) is tracked in
**MIOS-AIOS-MULTIAGENT-EXECUTION-PLAN-2026-06-14.md**. It is gated behind the P0 VRAM
decision (heavy lanes) and is multi-session, disjoint-owner work — out of scope for a
single hardening pass but the destination this plan feeds.

## Recommended execution order
P0.1 (confirm heavy-lane-off) → P1.2 (SSOT reconcile verify) → P1.3 (Hermes durability decision)
→ P2.4/5 (shell unify + launch polish) → P3/P4 depth → Roadmap waves.

## §Risks / caveats
- Hermes desktop fixes are **host-local** (AppData\Local\hermes) — see P1.3.
- Heavy lane re-enable will re-introduce the VRAM/thrash unless the budget guard (P0.1) ships first.
- Several P2+ items are 🔧 and need no decision — Claude can execute them on request, one at a time.

## What needs YOU vs what I can do next
- **Needs you (decision):** the 5 policy calls A–E above.
- **Needs you (action):** `/reset` the Hermes desktop app to verify the launch fix; verify Zen live.
- **I can do now, on your word:** every 🔧 item (P1.2, P2.4–6, P3/P4.7–12) — say which and I'll proceed.

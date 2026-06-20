<!-- AI-hint: Upstream-gap research (2026-06-20, multi-agent) + ordered fix plan for reliable AIOS Windows OS-control (UIA-targeted type/verify) and native per-turn env grounding. Records the root cause of the "typed into the wrong window" bug and the canonical UFO2/UIA fix, plus the structured <env> block decision. -->

# OS-control reliability + native env grounding — upstream gaps & plan (2026-06-20)

Multi-agent research (web: UFO2, UIA, pywinauto, Anthropic computer-use, MCP
resources; + MiOS code-grounding) into two operator mandates: (1) AIOS system/OS
control must be **reliable + verified**; (2) **every chat grounded in env details
every prompt, natively**. Triggered by the live bug: *"open notepad and type X"*
typed X into the **foreground chat app, not Notepad** (a read-only UIA probe found
the text sitting in the Hermes window's Edit control).

## Upstream-gap map

### OS-control (the typing bug)
| Canonical (UFO2 / UIA / pywinauto / Anthropic) | MiOS today | Gap |
|---|---|---|
| Act on a **specific AutomationElement** (FromHandle(hwnd) → FindFirst Document/Edit), never "the foreground" | `Invoke-TypeText` acts on `[AutomationElement]::FocusedElement` | **CRITICAL** — types into whatever wins the focus race (the chat app) |
| **SetValue** (writable ValuePattern) first; SetFocus+keystroke fallback | `Get-FocusedValueElement` only probes ValuePattern on FocusedElement | **CRITICAL** — Win11 Notepad's RichEditD2D Document control has **null ValuePattern** (TextPattern only) → always the racy SendKeys path |
| **Read back the SAME targeted element** (TextPattern.DocumentRange.GetText) | reads FocusedElement + foreground-title diff | **HIGH** — can verify the wrong window |
| Focus the **Windows** target via the executor (returns hwnd) | compound chain calls `focus_window` → the **Linux** `mios-window focus` verb | **HIGH** — wrong path for a Windows target; the hwnd it already has is discarded |
| Precondition gate (IsEnabled/IsVisible) + newest-window disambiguation | none | MEDIUM |

### Env grounding
| Canonical | MiOS today | Gap |
|---|---|---|
| Native per-turn env in a **system-role** block (Claude-Code `<env>`), live values each turn | `_env_grounding()` already threaded into ~12 hops — **mechanism exists + is correct** | INFORMATIONAL — it was unreconciled in CLAUDE.md and was **prose** (an 8B parses it unreliably) |
| Volatile/large state on-demand via tools | already so (`sys_env_snapshot`, `mios_apps`) | keep as-is |

Key reconciliation: a **system-role** env block is the canonical "every prompt
grounded" mechanism and is **distinct** from the banned `pre_llm_call`
**user-message** pre-inject. Both mandates are satisfied at once.

## Plan (ordered by leverage)

**DONE this session (verifiable, no app launch):**
- ✅ Verdict honesty: `mios-pc-control._exit_on_verdict` now **fails closed** (`f010f8b`) — type can't report success on an undeterminable read-back (10/10 unit).
- ✅ Env item 6: CLAUDE.md reconciled — native system-role `<env>` block is the required mechanism; user-message pre-inject is the banned one.
- ✅ Env item 7: structured `<env>` block (`_env_block()` in server.py) prepended to `_env_grounding()` — parseable key:value (timezone/surface/host/os/cwd/user/language/location+source), reusing the same getters + location-chain; additive (prose kept, no regression). Renders verified; live chat 200.

**REMAINING — OS-control typing (operator must live-test the write path; agent is barred from launching/typing):**
1. **Plumb a target window** through `/input/type` + `Invoke-TypeText` (`mios-oscontrol-server.ps1`): add `Resolve-EditElement($hwnd|$title)` = `FromHandle(hwnd)` → `FindFirst(Descendants, Document|Edit)`; gate IsEnabled/!Offscreen; `$el.SetFocus()`. Zero-target = today's behaviour (back-compat).
2. **Branch the write** on the resolved control's pattern: writable ValuePattern → `SetValue` (atomic, race-free); else (Notepad RichEditD2D) `SetFocus`+keystroke.
3. **Read back the SAME element** (`Get-ElementText`: ValuePattern else TextPattern.DocumentRange.GetText), strict + fail-closed; new reason `no_edit_control_in_target`.
4. **Route compound focus through the WINDOWS executor** (`server.py` ~23228) — capture the returned hwnd, pass `{text,hwnd,title}` to `pc_type` (extend `[verbs.pc_type]` in mios.toml + `mios-pc-control` type branch). Today it calls the Linux focus verb.
5. Newest-window preference + IsEnabled/IsVisible gate in `Resolve-TargetWindows`.

**REMAINING — env (low):**
8. Source the `<env>` static facts from one cached `sys_env` snapshot; recompute only volatile per-turn; keep open-windows/process-list on-demand (no token bloat).

Verification note: items 1–5 change the **write** path (typing), which the agent
cannot validate without launching/typing on the operator's screen (binding rule).
Each is operator-live-test: "open notepad and type hello" must land in Notepad,
not the chat app. Read-only `ui-list` probes can confirm `Resolve-EditElement`
finds a Notepad Document control without typing.

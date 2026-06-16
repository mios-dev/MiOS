<!-- AI-hint: Reference for the UNIFIED MiOS AI pipeline — how every front-end is a thin client to the agent-pipe orchestrator (:8640), the route-by-source anti-fabrication grounding strategy, OpenAI-standard tool-loop/tool-schema conformance, and the typing/OS-control execution path. Records what was built + verified live on 2026-06-16.
     AI-related: /usr/lib/mios/agent-pipe/server.py, /usr/bin/mios, /usr/sbin/@, /usr/sbin/hermes, /var/home/mios/.hermes/config.yaml, /usr/share/mios/windows/mios-oscontrol-server.ps1, /usr/libexec/mios/mios-pc-control, /usr/share/mios/mios.toml
     AI-functions: (reference doc — no functions) -->
> _FHS: /usr/share/mios/doc/concepts/unified-ai-pipeline-2026-06-16.md_
> CONCEPT/REFERENCE. How the MiOS AI pipeline is unified, grounded, and
> OpenAI-standard. Operator directives 2026-06-16: "UNIFY THE MiOS AI PIPELINE",
> "all tool available anywhere to any agent", "research proper patterns and loops
> to OpenAI standards", "refine tools to be perfected to AIOS systems and the MiOS
> environment", "MIOS AI ONLY USES UIA". SSOT remains the code + mios.toml; this
> documents the resulting architecture.

# Unified MiOS AI pipeline

## One orchestrator, many thin clients
Every front-end is a THIN client to the **agent-pipe orchestrator at `:8640`**
(served model `MiOS-Agent`); the orchestrator owns refine → route → dispatch /
native-loop / council → server-side broker execution → polish. No front-end runs
its own weak tool-loop.

| Front-end | Path to :8640 |
|---|---|
| `mios <prompt>` / `@<prompt>` | `/usr/sbin/@` → `exec /usr/bin/mios` (ENDPOINT `:8640`, model `MiOS-Agent`, `use_tools=False`) |
| OWUI | `mios-agent-pipe` pipe → `:8640` |
| Desktop Hermes app | `config.yaml` provider → `:8640`, `toolsets:[]` |
| Terminal `hermes` REPL | `/var/home/mios/.hermes/config.yaml` `model.provider: custom:mios-orchestrator` (`:8640/v1`, `MiOS-Agent`) |

`MiOS-Hermes` (`:8642`) is a LEAF the orchestrator may call, never a public
entrypoint. The REPL config is SEPARATE from the gateway config
(`HERMES_HOME=/var/lib/mios/hermes`) so routing the REPL to `:8640` does NOT loop
the gateway.

## Route-by-source grounding (anti-fabrication)
`web` is the ONLY external `[routing.domains]` domain; everything else targets
THIS machine. The orchestrator grounds each turn on its real source so a small
local model can never answer from training memory:

- **Local domain** (files/system/packages/…): NEVER web-search; use the local
  tools. A standalone "find X" no longer web-searches or guesses a path.
- **Arg-requiring reads fabricate without a deterministic pre-fetch.** A small
  non-tool_choice model SKIPS `web_search` (needs a query) / file-search (needs a
  filename) and answers from memory. So the orchestrator PRE-FETCHES + injects the
  live result, in BOTH the native-loop and the client-tools gate:
  - `web` domain → `web_search` prefetch.
  - `files` domain → `everything_search`/`fs_search` prefetch (filename token).
- **No-arg local reads** (`system_status`, `list_windows`) the model calls
  reliably → no prefetch needed.
- **Deterministic OS actions** ("open X", "type 'Y'") take a server-side
  fast-path (launch + read-back-verified type-chain), even on the client-tools
  path — bypassing the weak hybrid.
- Output-side `_strip_ungrounded_figures` drops invented $/%/figures the polish
  model added that aren't in the sources.

## OpenAI-standard loops + tools
- **Loop** (`_v1_secondary_tool_loop` + `_exec_tool_calls`): the canonical
  send → `tool_calls` → execute all → append `{role:tool, tool_call_id, content}`
  → re-invoke → terminate on no tool_calls; `SECONDARY_TOOL_MAX_ITERS` == OpenAI's
  `max_turns`; runaway/loop-signature guard.
- **`parallel_tool_calls`**: per-endpoint (`_endpoint_supports_parallel_tools`,
  `[dispatch].parallel_tools_hints`). Capable heavy lane → OpenAI-default True;
  small lanes → False (they malform parallel calls).
- **Tool schemas** (`_verb_to_openai_tool`): strict-mode — `strict:True`,
  `additionalProperties:False`, every prop in `required`, optional params as
  nullable `[type,"null"]`, enums on constrained params, detailed descriptions,
  pretraining-familiar `model_name` aliases. One SSOT `_VERB_CATALOG` → three
  projections (MCP / OpenAI tools / A2A skills).
- **All tools to any agent**: a focused in-context core + a guaranteed
  `tool_search` discovery floor in every agent surface (reach any of 86+ verbs
  anywhere) — exactly OpenAI's "keep <~20 in context, defer via tool search".
- Still on Chat Completions (the standard loop); a Responses-API migration is
  optional, not required.

## Typing / OS-control execution
- Typing is **UIA-first** (`ValuePattern.SetValue`) — no keystrokes, so no menubar
  activation, no dropped chars, immune to UIPI/foreground races; keystroke
  (`SendKeys`) is a FALLBACK only when a control exposes no writable UIA pattern.
- The window-focus op uses `SystemParametersInfo(SPI_SETFOREGROUNDLOCKTIMEOUT=0)`
  + `AllowSetForegroundWindow` (NOT an Alt-tap, which activated the menubar) to
  win foreground without a menu-triggering keystroke.
- `pc_type` STRICT read-back (UIA value / foreground title) verifies the exact
  text landed; the retry selects-all before re-typing so it REPLACES (no garble).
- The mios-pc-control wrapper distinguishes "executor unreachable" from "reachable
  but the handler errored" and surfaces the real reason (e.g. "Access is denied —
  session disconnected/locked or an elevated foreground window (UIPI)").

## Environment limits (operator decisions, surfaced honestly — not code gaps)
- Typing into an ELEVATED foreground window needs the OS-control executor run
  elevated (a security tradeoff: an admin HTTP input-injector).
- Win11 **Store** Notepad exposes NO writable UIA pattern (a Windows limitation),
  so it uses the menubar-safe keystroke path; UIA SetValue works for any
  ValuePattern editor.
- Typing requires the operator's interactive session CONNECTED (SendKeys cannot
  reach a disconnected desktop).

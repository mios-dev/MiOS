# MiOS native OS-agent patterns — what's actually industry-standard in 2026

> Operator directive 2026-05-18: "what am I missing?? are those even right?
> WHAT's native to the Whole technology stack(s) GLOBALLY for MiOS--What's
> going to make these simple things like; 'open x' or 'move x to the
> foreground' or 'center x' 'launch to top right/left/bottom/top/middle/
> center/etc' or 'close x' or open x in x(or y) ... whilst STILL not being
> hardcoded and computationally cheap/offline/locally computed ... What's
> ALL NATIVE to OpenAI API and industry standards and patterns ... Native
> Linux FHS/Bootc bootable OCI image(s) ... DAY-0/offline/in-code/
> EVERYTHING! Research!!!"

## TL;DR

For an OS-native agent stack like MiOS, the 2026 industry pattern is a
**three-layer composition**, none of it regex-driven:

1. **A small typed toolset** exposed via OpenAI strict function-calling
   (JSONSchema with enums) — the model picks valid positions/sizes/
   actions naturally, no SOUL.md ban lists required.
2. **MCP (Model Context Protocol) server** — wraps the same toolset in
   the open JSON-RPC standard Anthropic + OpenAI + Google now all
   support, so the same MiOS verbs are usable from Claude Desktop /
   Cursor / any future MCP-aware client without per-integration code.
3. **Anthropic Computer Use fallback** — for the long tail (UI without
   a clean API), the model gets `screenshot`/`mouse_click`/`keyboard_type`
   and reasons visually. Only used when no typed tool covers the intent.

All three patterns are LOCAL-EXECUTABLE (the tool execution is your
code; the LLM just emits structured tool_calls), so Day-0/offline
constraints are satisfied: the MCP server + the function-calling
runtime + Computer Use loop all run on the operator's machine.
Models can be local (Ollama) OR cloud (OpenAI/Anthropic) — the
tool surface is identical.

## What's wrong with the current MiOS approach

The current shape is **regex-driven post-processing on top of a
mostly-text agent loop**:

* `mios_verbs.py` exposes `launch_app(name)` -- only `name`. Position,
  size, args all live in shell-only env vars (`MIOS_LAUNCH_POSITION=
  left mios-find ... | bash`). The model has to KNOW that env-var
  convention from SOUL.md prose -- which it forgets, and which can't
  be schema-validated.
* `mios-window` is a bash shim with subcommands (`close`/`center`/
  `move`/etc); the model accesses it via `terminal: mios-window
  close "X"` -- two layers of string parsing.
* `_KNOWN_AGENT_ERROR_RE`, `_DETAILS_BLOCK_RE`, `_THINK_TAG_RE`, the
  polish ban lists ("NEVER report 'launched' unless...") -- all
  post-hoc fixes for the agent saying the wrong thing in text.
* SOUL.md is a 700-line rule book the agent re-reads every turn,
  and only sometimes follows.

Every failure mode the operator's flagged maps to either:
* tool surface that can't express the intent in the call itself, OR
* prompt rules that the model ignored.

The fix is not more rules; it's a richer **typed tool surface** so
the schema enforces what the rule was trying to say.

## Layer 1 — OpenAI strict function-calling with enums

The right way to expose `launch_app` is:

```python
{
  "name": "open_app",
  "description": "Open a desktop app on the operator's screen, optionally placing the window. Works for Windows apps (Steam/Epic/Xbox/protocol-handlers/.exe) and Linux GUI apps (any /usr/bin/<bin> via WSLg). For URLs use `open_url`; for images use `show_image`; for maps use `open_map`.",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["name"],
    "properties": {
      "name": {
        "type": "string",
        "description": "App name or substring (case-insensitive). Resolved through the canonical launch chain (Windows games inventory / start menu / MiOS shim / Linux PATH)."
      },
      "args": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Extra positional arguments (e.g. a file path for `notepad`)."
      },
      "position": {
        "type": "string",
        "enum": [
          "center", "left", "right", "top", "bottom",
          "top-left", "top-right", "bottom-left", "bottom-right",
          "maximize", "as-is"
        ],
        "description": "Where to place the new window on the primary monitor. `as-is` = leave wherever the OS spawned it."
      },
      "monitor": {
        "type": "integer",
        "description": "0-indexed monitor to target. 0 = primary. Out-of-range = primary."
      }
    }
  },
  "strict": true
}
```

With OpenAI's strict mode (`response_format: json_schema` or
`tool_choice: required` with `strict: true`), the model CANNOT emit
`position: "top-right-ish"` — the schema rejects it. The model
NATIVELY learns the valid placement enum from the schema and picks
the right value for "launch on the top right of my screen". No
SOUL.md rule needed; no regex post-check.

Counterpart tools (replace the current shim+terminal chain):

```
focus_window(title_pattern)
move_window(title_pattern, position, monitor=0)
close_window(title_pattern, graceful=true)
screen_layout()  -> {monitors: [{index, width, height, primary, scale}]}
list_windows()   -> [{title, hwnd, pid, monitor, visible}]
open_url(url, browser=null, position=null)
open_map(query, mode="search"|"directions", origin=null, position=null)
show_image(query, position=null)
take_screenshot(target="primary"|"window:<title>", action="save"|"clipboard"|"open")
launch_app_in(app, file_or_url)  -- the "open X in Y" intent
```

All under one cohesive `mios_desktop` toolset. Each schema-typed
parameter teaches the model the surface. The agent's "rule book"
becomes ~50 lines of JSON instead of 700 lines of prose.

**Sources:**
* [OpenAI Function Calling guide](https://platform.openai.com/docs/guides/function-calling) — strict mode + JSONSchema enums
* [OpenAI Structured Outputs intro](https://openai.com/index/introducing-structured-outputs-in-the-api/) — "every required field will be present, every type will be correct, every enum value will be valid"

## Layer 2 — MCP (Model Context Protocol) server

[MCP](https://modelcontextprotocol.io/specification/2025-11-25) is the
open JSON-RPC standard for exposing tools/resources/prompts to LLM
hosts. Anthropic introduced it Nov 2024; by early 2026 OpenAI + Google
DeepMind also support it, 500+ public servers exist, 97M monthly SDK
downloads.

MiOS should ship `mios-mcp-server` (Python + the official `mcp` SDK)
that wraps the typed toolset above. Then ANY MCP host can use MiOS
verbs:

* **Claude Desktop** — operator adds `{"mios": {"command":
  "/usr/libexec/mios/mios-mcp-server"}}` to claude_desktop_config.json,
  Claude can now `open_app`, `move_window`, etc. against the MiOS host.
* **Cursor / VS Code with Continue** — same MCP server config.
* **OWUI** — install the [MCP-OpenWebUI bridge](https://github.com/
  open-webui/mcpo) or use the future native MCP support; same MCP
  server, same tools.
* **Custom agent** (Hermes, future OpenCode) — `mcp.connect("mios")`
  and call the tools directly with `tool_call` shape.

This decouples the tool implementation from any single client. Today's
mios_verbs.py is OWUI-shaped (Pydantic `Tools` class); an MCP server
is universal.

**Sources:**
* [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25)
* [MCP Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)
* [MCP Complete 2026 Guide](https://sureprompts.com/blog/model-context-protocol-mcp-complete-guide-2026)
* [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)

## Layer 3 — Anthropic Computer Use fallback

For the long tail (vendor app with no clean API; web-only flow), the
2026 native pattern is [Anthropic's Computer Use](https://platform.
claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool) —
agent gets `screenshot` / `mouse_click` / `keyboard_type` /
`scroll` tools, takes a screenshot, reasons visually about UI
elements, acts. Loop until done.

For MiOS this would be a `mios-cu-server` (MCP wrapper) exposing the
operator's screen + input via the existing `mios-screenshot` /
`mios-pc-control` / `mios-window` primitives. Used ONLY when the
typed tool above doesn't cover the intent.

The strict ordering: try typed tool first (cheap, deterministic),
fall back to Computer Use (expensive, vision pass per step) only when
necessary.

**Sources:**
* [Anthropic Computer Use tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
* [Anthropic Computer Use API guide](https://www.digitalapplied.com/blog/anthropic-computer-use-api-guide)
* [Claude Computer Use vs OpenAI CUA — WorkOS](https://workos.com/blog/anthropics-computer-use-versus-openais-computer-using-agent-cua)

## Migration plan for MiOS (Day-0 / Bootc / FHS-compliant)

All paths image-immutable; no /etc writes; runs offline against local
Ollama; works identically against any cloud OpenAI/Anthropic backend
when the operator opts in.

### Step 1 (small, ship-this-week)
**Extend `mios_verbs.py` Tools class** with the typed surface:
* `open_app(name, args?, position?, monitor?)`
* `focus_window(title)`
* `move_window(title, position, monitor?)`
* `close_window(title, graceful?)`
* `list_windows()`
* `screen_layout()`
* `open_url(url, browser?, position?)`
* `open_map(query, mode?, origin?, position?)`
* `show_image(query, position?)`
* `take_screenshot(target?, action?)`

Each method's docstring + type hints become the JSONSchema OWUI
sends to the model. Add `Literal[...]` types for the enum positions
(OWUI's introspector emits these as JSONSchema enums automatically).

Replace SOUL.md prose rules with the schema. Drop ~300 lines of
"NEVER do X / ALWAYS use Y" -- the schema enforces them.

### Step 2 (next-week)
**Ship `/usr/libexec/mios/mios-mcp-server`** — Python stdio MCP server
wrapping the same Tools class. Single source of truth for the toolset.
Add `claude_desktop_config.json` snippet to `/usr/share/mios/docs/`
so operators can paste it into Claude Desktop to use MiOS from there.

### Step 3 (next-month)
**Drop the regex tower**: `_KNOWN_AGENT_ERROR_RE`,
`_DETAILS_BLOCK_RE`, `_LEADING_THOUGHT_RE` heuristics. The Critic
agent + structured tool_history (already shipped in phase-1/phase-2)
+ schema-enforced tool calls eliminate the failure modes those
regexes were patching.

### Step 4 (when needed)
**Computer Use fallback** for the long tail. `mios-cu-server` MCP
wrapping the existing `mios-screenshot` + `mios-pc-control`
primitives.

## What the operator gets

* **"launch notepad on top right"** → model emits
  `open_app(name="notepad", position="top-right")`. Single call. No
  shell parsing, no env-var prelude, no SOUL.md rule about
  positioning syntax. The enum tells the model what's valid.
* **"close the chrome window"** → `close_window(title="Google Chrome",
  graceful=true)`. The `graceful` enum (or bool) maps to WM_CLOSE vs
  TerminateProcess — schema makes the choice explicit.
* **"open this file in vscode"** → `launch_app_in(app="vscode",
  file_or_url="/path/to/file.txt")`. The "in" intent is a separate
  function so the model doesn't have to compose two calls.
* **Long reasoning time vanishes** — the model picks one tool, calls
  it, done. No multi-step planner needed for single-intent asks.

All offline (tool runs locally on the MiOS host). All Day-0 (toolset
ships in /usr/share/mios/owui/tools/ + /usr/libexec/mios/mios-mcp-
server; bootc layer). All OpenAI-API-compliant (standard JSONSchema
+ tool_call shape). All FHS-correct (no /etc writes for normal
operation; user-facing knowledge auto-registers via
mios-owui-apply-knowledge).

## Sources

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)
- [MCP Complete 2026 Guide](https://sureprompts.com/blog/model-context-protocol-mcp-complete-guide-2026)
- [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP — USB-C for AI Native Applications](https://www.essamamdani.com/blog/complete-guide-model-context-protocol-mcp-2026)
- [Anthropic Computer Use tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- [Anthropic Computer Use API Guide](https://www.digitalapplied.com/blog/anthropic-computer-use-api-guide)
- [Anthropic Computer Use vs OpenAI CUA](https://workos.com/blog/anthropics-computer-use-versus-openais-computer-using-agent-cua)
- [Claude Computer Use 2026 setup](https://blog.laozhang.ai/en/posts/claude-computer-use)

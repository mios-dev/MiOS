"""
title: MiOS-Agent
author: MiOS
version: 1.2.0
description: |
  Consolidated MiOS systems agent. The canonical user-facing entry
  point in OWUI. Owns three concerns end-to-end so they always fire
  regardless of OWUI's routing decisions (the global Filter chain
  can be bypassed when a Pipe takes over):

    1. PROXY -> prefilter (:8641) -> hermes (:8642). Streams SSE
       chunks back to the operator as fast as they arrive. Unbounded
       sock_read so long CPU-bound tool turns don't TransferEncoding-
       Error the response.

    2. LIVE EMITS. Polls /var/lib/mios/hermes-tail/latest.json (the
       root-tail bridge populated by mios-hermes-tail.service) on a
       background task while the stream is open, and pushes each
       new event through __event_emitter__ so the operator SEES
       "calling terminal: mios-find beamng" / "max retries hit" in
       real time -- not after the chat completes.

    3. NARRATION COLLAPSE. Buffers content until a line boundary,
       routes each whole line through _is_narration_line() and wraps
       narration in <think>...</think> so OWUI renders it inside its
       native collapsible Thinking widget. Final-answer lines pass
       through verbatim. Operator directive 2026-05-16: "ALL THESE
       MIOS-HERMES AGENTS THINKING PRINTS COULD BE EMMITED AND/OR
       COLLAPSABLE AS THINKING IN OWUI".

  Default BACKEND_URL is 127.0.0.1 (the host-process prefilter).
  Previous container-internal address (host.containers.internal)
  was a leftover from the container-era Quadlet -- OWUI runs as a
  host process now, so that address never resolved.
"""

from pydantic import BaseModel, Field
import json
import os
import re
import asyncio
import time
from typing import AsyncGenerator, Awaitable, Callable, Optional

import aiohttp


# ─── Qwen-style XML function-call markup the model sometimes leaks ────
QWEN_FUNCTION_RE = re.compile(
    r"<function=([a-zA-Z_-]+)>\s*"
    r"(?:<parameter=([a-zA-Z_-]+)>\s*(.*?)\s*</parameter>\s*)*"
    r"</function>(?:\s*</tool_call>)?",
    re.DOTALL,
)


# ─── Narration line classifier (kept IN SYNC with mios_antimeta_filter) ──
# Anchored to start-of-line; matches the meta-speak the operator wants
# collapsed into <think>...</think> rather than showing in the answer.
NARRATION_LEADERS = [
    r"^let me\b", r"^let.s\b", r"^i.ll\b", r"^i.m going to\b",
    r"^i.m about to\b", r"^i need to\b", r"^i.ll need to\b",
    r"^first,?\s*i\b", r"^next,?\s*i\b", r"^now,?\s*i\b",
    r"^i.ve (loaded|updated|checked|verified|noted)\b",
    r"^i.?ll try (a different|another) approach\b",
    r"^i.?ll take a (simpler|different) approach\b",
    r"^i.?ll approach this (differently|another way)\b",
    r"^based on the available tools\b",
    r"^i need to analyze\b", r"^let me analyze\b",
    r"^i should\b", r"^i will now\b",
    r"^(thinking|reasoning):\s",
]
NARRATION_RES = [re.compile(p, re.IGNORECASE) for p in NARRATION_LEADERS]


def _is_narration_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    for pat in NARRATION_RES:
        if pat.search(s):
            return True
    return False


# ─── hermes-tail bridge polling ──────────────────────────────────────
HERMES_TAIL_PATH = "/var/lib/mios/hermes-tail/latest.json"
TAIL_POLL_INTERVAL_S = 0.4

_TAIL_ICONS = {
    "max_retries":    "❌",
    "invalid_tool":   "⚠️",
    "retry":          "↻",
    "delegate_spawn": "🚀",
    "synthesis":      "🔀",
    "subagent_done":  "✓",
    "tool_call":      "🛠️ ",
}


class Pipe:
    class Valves(BaseModel):
        BACKEND_URL: str = Field(
            default="http://host.containers.internal:8642/v1",
            description="OpenAI-compat backend = hermes-agent gateway on :8642 (direct). The prefilter @ :8641 sat in front for delegate_task forcing but the pipe now does refinement directly, so prefilter is bypassed -- removes a moving part and fixes the ClientConnectorError when prefilter is down (operator-flagged 2026-05-17). OWUI runs in a podman Quadlet so the host is reached via host.containers.internal.",
        )
        BACKEND_MODEL: str = Field(
            default="hermes-agent",
            description="Model name to pass upstream. Direct dispatch to hermes uses its native model id `hermes-agent`.",
        )
        BACKEND_KEY: str = Field(
            default_factory=lambda: os.environ.get("API_SERVER_KEY") or os.environ.get("OPENAI_API_KEY") or "",
            description="Bearer key for the backend. Defaults to API_SERVER_KEY / OPENAI_API_KEY from the OWUI container env.",
        )

        # ── In-pipe CPU refinement (operator-architecture 2026-05-17) ──
        # MiOS-Agent IS the CPU refiner -- it sits in front of hermes,
        # takes the user's raw prompt, calls a small CPU model on
        # Ollama, and forwards a refined / contextualized prompt to
        # the heavy GPU orchestrator. Sub-second target. Operator:
        # "OWUI's MIOS_AGENT OPERATES ON THE CPU MODEL ... QUICKLY
        # REFINING THE USERS PROMPTS WITH MORE CONTEXT AND CLEARER
        # DIRECTIONS FOR HERMES AGENTS/DELEGATED SUB-AGENTS".
        REFINE_ENABLED: bool = Field(
            default=True,
            description="Run a quick CPU-model refinement pass on every user prompt before forwarding to hermes.",
        )
        REFINE_MODEL: str = Field(
            default="qwen2.5-coder:7b",
            description="Small NON-THINKING CPU model used for refinement. qwen3.x family models all emit to message.thinking with empty message.content even with /nothink directive (modelfile-level thinking-mode override). qwen2.5-coder:7b is the available non-thinking model that produces content directly. ~4.7 GB on CPU; cold load 30-90s on WSL2 disk, warm calls 3-10s. Loaded once with keep_alive=-1.",
        )
        REFINE_ENDPOINT: str = Field(
            default="http://host.containers.internal:11434",
            description="Ollama endpoint for the refine call. Hits /api/chat (NOT /v1, which drops options field).",
        )
        REFINE_TIMEOUT_S: int = Field(
            default=180,
            description="Hard cap on the refine call. Should comfortably exceed warm-call latency on the host's CPU. On timeout the pipe falls through to original prompt (NOT 503; pipe is OWUI-facing and 503 would be a bad UX). 60s was insufficient with the expanded refiner system prompt (operator-flagged 2026-05-17 'refine timeout too!!'); 180s gives a 3x safety margin for warm calls + room for cold first calls + occasional CPU contention.",
        )
        REFINE_MAX_TOKENS: int = Field(
            default=220,
            description="Cap refine output. Smaller = faster turn. 220 tokens fits INTENT + 2-3 step PLAN comfortably; dropped from 300 to keep refine latency under the new 180s ceiling on a busy CPU.",
        )
        REFINE_SKIP_SHORT: bool = Field(
            default=True,
            description="Skip refinement on greetings/acks (hi/hello/thanks/bye) -- no value added, just adds latency.",
        )

        DISPLAY_NAME: str = Field(
            default="",
            description="Suffix appended to the FUNCTION row name in OWUI's model dropdown. Leave empty so dropdown shows just 'MiOS-Agent'.",
        )
        EMIT_STATUS: bool = Field(
            default=True,
            description="Emit status events ('refining...', 'dispatching to hermes...', tool calls).",
        )
        EMIT_HERMES_TAIL: bool = Field(
            default=True,
            description="Live-poll /var/lib/mios/hermes-tail/latest.json and emit each new event during the stream.",
        )
        COLLAPSE_NARRATION: bool = Field(
            default=True,
            description="Buffer per-line, wrap meta-speak in <think>...</think> (OWUI collapsible).",
        )
        TIMEOUT_S: int = Field(
            default=0,
            description="Total HTTP timeout in seconds (0 = unbounded, recommended for CPU-bound tool turns).",
        )

        # ── Output refinement (operator-architecture 2026-05-17) ──
        # The downstream agent dispatch (hermes-agent today; later
        # opencode / MCP / delegated subagents the same way) emits a
        # mix of narration, tool I/O, and final result. MiOS-Agent
        # wraps the WHOLE raw stream as <details type="reasoning">
        # collapsed thinking, then runs a CPU polish pass to produce
        # the operator-facing answer.
        #
        # Operator quote: "ALL MiOS-Agent(OWUI)'s dispatches
        # (MiOS-Hermes, MiOS-OpenCode, etc) are always capturing their
        # outputs as thinking and providing an appropriate final
        # answer normally in OWUI chats".
        POLISH_ENABLED: bool = Field(
            default=True,
            description="After the agent stream ends, run a CPU pass to produce the operator-facing final answer. The raw agent output is preserved as a collapsed <details type='reasoning'> block above. Disable to passthrough hermes raw (legacy behavior).",
        )
        POLISH_MODEL: str = Field(
            default="qwen2.5-coder:7b",
            description="CPU model used for the output polish pass. Same model+keep_alive as the input refiner so cold-load happens once.",
        )
        POLISH_TIMEOUT_S: int = Field(
            default=180,
            description="Hard cap on the polish call. Falls back to raw hermes output on timeout (better than empty answer).",
        )
        POLISH_MAX_TOKENS: int = Field(
            default=600,
            description="Cap polished output. 600 tokens fits a multi-paragraph + table answer; bigger answers can pass through raw.",
        )
        POLISH_SKIP_SHORT_CHARS: int = Field(
            default=240,
            description="If the raw agent output is shorter than this and contains no narration markers, pass through unpolished -- no value in spinning up the CPU model for a one-liner result.",
        )
        AGENT_THINKING_LABEL: str = Field(
            default="🧠 MiOS-Hermes thinking + tools (click to expand)",
            description="The <summary> rendered above the collapsed reasoning block. Per-agent label so the operator can tell which agent (hermes / opencode / etc.) produced the thinking.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.name = "MiOS-Agent"

    def pipes(self):
        # OWUI dropdown shows `<function.name><pipe.name>` with no
        # separator. The function row's name is already "MiOS-Agent",
        # so we leave the pipe.name EMPTY -- otherwise the dropdown
        # reads "MiOS-AgentMiOS-Agent" (operator-flagged 2026-05-17).
        return [{"id": "mios-agent", "name": self.valves.DISPLAY_NAME}]

    async def _emit(
        self,
        emitter: Optional[Callable[..., Awaitable[None]]],
        description: str,
        done: bool = False,
    ) -> None:
        if not (self.valves.EMIT_STATUS and emitter):
            return
        try:
            await emitter({
                "type": "status",
                "data": {"description": description, "done": done},
            })
        except Exception:
            pass

    async def _tail_watcher(
        self,
        emitter: Optional[Callable[..., Awaitable[None]]],
        stop: asyncio.Event,
    ) -> None:
        """Background task: poll hermes-tail JSON, emit new events as they arrive.
        Tracks last-seen event ts per-task so we never re-emit."""
        if not (self.valves.EMIT_HERMES_TAIL and emitter):
            return
        last_ts = 0.0
        while not stop.is_set():
            try:
                st = os.stat(HERMES_TAIL_PATH)
                if st.st_mtime > 0:
                    with open(HERMES_TAIL_PATH) as f:
                        payload = json.load(f)
                    for ev in payload.get("events", []):
                        ev_ts = ev.get("ts", 0)
                        if ev_ts > last_ts:
                            last_ts = ev_ts
                            kind = ev.get("kind", "")
                            detail = ev.get("detail", "")
                            icon = _TAIL_ICONS.get(kind, "·")
                            await self._emit(emitter, f"{icon} {detail}")
            except (OSError, json.JSONDecodeError):
                pass
            try:
                await asyncio.wait_for(stop.wait(), timeout=TAIL_POLL_INTERVAL_S)
            except asyncio.TimeoutError:
                continue

    # ─── CPU REFINEMENT (in-pipe, sub-second target) ─────────────
    # Architecture: MiOS-Agent (this pipe) IS the prompt enhancer.
    # Operator: "OWUI's MIOS_AGENT OPERATES ON THE CPU MODEL ...
    # IS QUICKLY REFINING THE USERS PROMPTS WITH MORE CONTEXT AND
    # CLEARER DIRECTIONS FOR HERMES AGENTS/DELEGATED SUB-AGENTS".
    # The pipe owns this step end-to-end:
    #   1. Receive raw user text
    #   2. Call a small CPU model on Ollama (default qwen3.5:4b)
    #      with a tight system prompt -- num_predict capped low,
    #      keep_alive=-1, num_gpu=0, native /api/chat endpoint
    #   3. Return the refined text -- forwarded as the user message
    #      to the prefilter -> hermes chain
    #
    # The refiner runs INLINE in the pipe so the operator sees it
    # as a discrete OWUI status emit ("🧠 refining via qwen3.5:4b
    # on CPU...") rather than as an invisible sidecar pre-step.

    # Curly-quote (U+2019) tolerant. Operator-flagged 2026-05-17:
    # "How's it going?" (with smart-quote apostrophe) fell through the
    # gate -> triggered the dashboard rule and the agent dumped
    # mios-system-status as the answer to a greeting. Both ' (U+0027)
    # and ' (U+2019) now match the optional apostrophe slot.
    _CONVERSATIONAL_RE = re.compile(
        r"^\s*(hi|hello|hey|yo|howdy|sup|gm|gn|"
        r"good (morning|afternoon|evening|night)|"
        r"ok|okay|kk|alright|"
        r"thanks|thx|ty|thank you|"
        r"cool|nice|great|got it|sounds good|sgtm|"
        r"sure|yes|no|yep|nope|yeah|nah|"
        r"bye|cya|goodbye|later|peace|seeya|"
        r"what[’']?s (up|new|good|happening)|"
        r"how['’]?s (it going|things|things today|things going|life|stuff)|"
        r"how (are|have|you been|are things|are you|are ya|you doing|you been|is it going|is everything)|"
        r"what'?s (going on|happening)|"
        r"what do you (want|wanna|got|need))[!?.,\s]*$",
        re.IGNORECASE,
    )

    # Refine system prompt — tight, MiOS-aware, examples-driven.
    # Operator directive 2026-05-17: "refiner needs tighter system
    # prompt for guidance in the MiOS Environments and deployments
    # -- should delegate tools and skill calls hints in the
    # refinements". The model gets the MiOS verb table + skill
    # table + delegate guidance + 2 few-shot examples so its
    # output reaches for the right helper.
    _REFINE_SYSTEM = (
        "You are MiOS-Agent, the prompt-enhancement front of the MiOS\n"
        "agent stack. Rewrite the user's raw request into a refined\n"
        "prompt the downstream MiOS-Hermes orchestrator (and its\n"
        "delegate_task sub-agents) can act on directly.\n"
        "\n"
        "## MiOS host context\n"
        "Fedora-bootc immutable OS, WSL2-hosted on Windows. The MiOS\n"
        "host CAN reach the Windows side via `mios-windows` (WSL\n"
        "interop). All AI is LOCAL (Ollama + Hermes-Agent + OWUI).\n"
        "Operator is `mios`. Everything offline-first per Law 7.\n"
        "\n"
        "## CRITICAL: only Hermes-side `terminal` is reliable\n"
        "Downstream Hermes does NOT see OWUI tools (launch_app(),\n"
        "everything_search(), system_status(), mios_apps(), mios_find()).\n"
        "Those are OWUI-Python surface helpers. Every PLAN step you\n"
        "emit MUST be runnable through Hermes's `terminal` tool. Translate\n"
        "every intent into shell commands using the helper binaries on\n"
        "the operator's $PATH:\n"
        "\n"
        "  intent                                   ->  terminal command\n"
        "  ──────────────────────────────────────────────────────────────\n"
        "  launch / open / start <app | game>       ->  mios-find \"<name>\" | bash\n"
        "  open browser to <url>                    ->  mios-open-url \"<url>\"\n"
        "  find file matching <pattern>             ->  mios-everything -n 20 \"<pattern>\"\n"
        "  list installed apps (filter)             ->  mios-apps --filter <substr>\n"
        "  dashboard / system status / GPU / disk   ->  mios-system-status\n"
        "  was app actually presented to operator?  ->  mios-window-active --present \"<name>\"\n"
        "  arbitrary windows command                ->  mios-windows ps \"<powershell>\"\n"
        "  arbitrary windows .exe                   ->  mios-windows launch \"<C:\\path\\or\\URI>\"\n"
        "  install package (any backend)            ->  mios-installer install <id> [--backend winget|dnf|flatpak] [--no-confirm]\n"
        "  search for installable package           ->  mios-installer search \"<query>\"\n"
        "  install a STEAM game by appid            ->  mios-steamcmd install <APPID>   (URI route -> Steam GUI; owned games)\n"
        "  install a free / dedicated-server steam content ->  mios-steamcmd install <APPID> --route cmd   (headless SteamCMD)\n"
        "  search steam store / get steam appid     ->  mios-steamcmd search \"<game name>\"\n"
        "  steam game info / install status         ->  mios-steamcmd {info|status|validate|update} <APPID>\n"
        "  list installed steam games               ->  mios-steamcmd list\n"
        "  open mios.html / configurator / settings ->  mios-html\n"
        "  take a screenshot / snap the screen      ->  mios-screenshot [--open] [--clipboard]\n"
        "  screenshot a specific window             ->  mios-screenshot --window \"<title-pattern>\" [--open]\n"
        "  open a markdown editor / preview window  ->  mios-md [<file.md>]  (or --text \"<inline md>\")\n"
        "  move/center/focus/resize a window        ->  mios-window {list|center|move|resize|focus|minimize|maximize|restore|close} \"<title>\" [args...]\n"
        "  close / quit / exit an app or game       ->  mios-window close \"<title-pattern>\"   (graceful WM_CLOSE; NEVER pkill / Stop-Process)\n"
        "\n"
        "## Hermes tools (these ARE visible to the downstream agent)\n"
        "- terminal                     run any bash command (incl. mios-*)\n"
        "- delegate_task(tasks=[...])   spawn parallel sub-agents\n"
        "- web_search / web_extract     local SearXNG\n"
        "- discord_send_message         post to operator's default channel\n"
        "- cronjob / cronjob_*          schedule recurring work\n"
        "- kanban_create / _list / _show / _complete / _block / _comment\n"
        "- memory_save / memory_search  per-host persistent memory\n"
        "- read_file / write_file       file operations\n"
        "- skill_view / skill_manage    load + edit MiOS skills\n"
        "\n"
        "## browser_navigate IS NOT 'open the browser'\n"
        "browser_navigate / _snapshot / _click / _type drive a HEADLESS\n"
        "Chrome-DevTools-Protocol session that the operator does NOT\n"
        "see. For 'open <url> in my browser' / 'go to <url>' the only\n"
        "correct call is `terminal: mios-open-url \"<url>\"` -- the operator\n"
        "needs the URL on their visible monitor, not in an invisible\n"
        "headless tab.\n"
        "\n"
        "## Output format\n"
        "INTENT: <one sentence of what the user actually wants>\n"
        "TOOLS:  <comma-separated Hermes tools that will execute>\n"
        "DELEGATE: <YES if independent fan-out makes sense, else NO>\n"
        "PLAN:\n"
        "  1. terminal: <exact shell command>\n"
        "  2. terminal: <exact shell command>\n"
        "  3. <verifier or formatting step>\n"
        "\n"
        "## Examples\n"
        "\n"
        "All examples below use <PLACEHOLDERS> instead of real app/topic/\n"
        "URL names. Substitute the operator's actual nouns at refine time.\n"
        "These are TEMPLATES, not recipes -- never echo a placeholder\n"
        "literally back to the operator.\n"
        "\n"
        "User: launch <APP-OR-GAME>\n"
        "INTENT: Launch the named app or game on the operator's monitor.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-find \"<APP-OR-GAME>\" | bash\n"
        "  2. terminal: mios-window-active --present \"<APP-OR-GAME>\"   # verify presented\n"
        "\n"
        "User: launch <APP1>, open a browser to <URL>, and launch <APP2>\n"
        "INTENT: Three independent surface actions: two app launches + one URL open.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-find \"<APP1>\" | bash\n"
        "  2. terminal: mios-open-url \"<URL>\"\n"
        "  3. terminal: mios-find \"<APP2>\" | bash\n"
        "  4. terminal: mios-window-active --present \"<APP1>\"   # repeat for each\n"
        "\n"
        "User: install <APP> on Windows           # (non-Steam, non-URI app — most common)\n"
        "INTENT: Install a Windows app via winget. Always SEARCH first to resolve\n"
        "        the canonical Publisher.AppId, then install -- guessing the id\n"
        "        almost always picks a typosquat or unrelated package.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-installer search \"<APP>\" --backend winget       # confirm canonical id\n"
        "  2. terminal: mios-installer install <Publisher.AppId> --backend winget --no-confirm\n"
        "  # NEVER: opening obsproject.com / winrar.com / etc. in the browser to download a .exe --\n"
        "  # winget IS the Windows installer surface; web downloads are an anti-pattern here.\n"
        "\n"
        "User: install <STEAM-GAME> on Steam       # owned game, agent doesn't know the appid yet\n"
        "INTENT: Install a Steam game via Valve's native install flow.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-steamcmd search \"<GAME-NAME>\"                # confirm canonical AppID\n"
        "  2. terminal: mios-steamcmd install <APPID>                       # default route: steam://install/<APPID> -> Steam GUI\n"
        "  3. terminal: mios-window-active --present \"Steam\"               # Steam UI hosts the install dialog\n"
        "\n"
        "User: install <LINUX-PACKAGE>           # bare lowercase word -> dnf; reverse-DNS -> flatpak\n"
        "INTENT: Install a Linux-side package on the MiOS host.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-installer install <id> --no-confirm   # backend auto-detected from id shape\n"
        "\n"
        "User: search for a <CATEGORY> tool I can install\n"
        "INTENT: Search every installer backend for matching packages.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-installer search \"<KEYWORD>\"\n"
        "  2. Propose the best match as `mios-installer install <ID>` to the operator.\n"
        "\n"
        "User: research <TOPIC> and post a recurring summary to discord\n"
        "INTENT: Set up a recurring research + Discord posting workflow.\n"
        "TOOLS: web_search, web_extract, discord_send_message, cronjob\n"
        "DELEGATE: YES\n"
        "PLAN:\n"
        "  1. delegate_task: [{web_search <TOPIC> news}, {web_search <TOPIC> details}]\n"
        "  2. Compose summary, discord_send_message to default channel.\n"
        "  3. cronjob to repeat at the operator-requested cadence.\n"
        "\n"
        "User: show me the MiOS dashboard / system status / GPU / disk / ollama models\n"
        "INTENT: Display the live MiOS system dashboard from real probes.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-system-status                           # returns JSON\n"
        "  2. Format the JSON into a markdown dashboard: GPU+VRAM, RAM, disk\n"
        "     table, services{failed,active,mios}, full ollama model list.\n"
        "     DO NOT add, invent, or guess any field -- only what the JSON\n"
        "     reports. If the binary fails, surface stderr verbatim.\n"
        "\n"
        "## Rules\n"
        "- Output ONLY the labeled handoff (INTENT / TOOLS / DELEGATE / PLAN).\n"
        "- No preamble, no markdown headers (`##`), no commentary.\n"
        "- Under 300 tokens total.\n"
        "- Every PLAN step is a real shell line the agent will paste\n"
        "  into `terminal:`. NEVER reference launch_app(), system_status(),\n"
        "  browser_navigate() in PLAN steps -- those are not visible to\n"
        "  Hermes. Use `mios-find`, `mios-open-url`, `mios-system-status`,\n"
        "  `mios-windows` etc. in `terminal:` instead.\n"
        "- For 'launch <X>' / 'open <X>' / 'start <X>' the FIRST tool\n"
        "  is ALWAYS `terminal: mios-find \"<X>\" | bash`. mios-find resolves\n"
        "  the canonical launch line + sets MIOS_LAUNCH_TITLE_HINT so the\n"
        "  result centers+focuses on the operator's monitor.\n"
        "- For 'open the browser to <url>' / 'go to <url>' the ONLY\n"
        "  correct call is `terminal: mios-open-url \"<url>\"`. NEVER\n"
        "  browser_navigate (headless; operator can't see).\n"
        "- For 'install <X> on Windows' / 'install <X>' (Windows context):\n"
        "  the ONLY correct path is `mios-installer search/install --backend\n"
        "  winget`. NEVER open a vendor download page (discord.com,\n"
        "  obsproject.com, mozilla.org, 7-zip.org, etc.) and ask the\n"
        "  operator to click through an installer wizard. winget IS the\n"
        "  Windows installer surface MiOS exposes -- bypassing it leaves\n"
        "  the operator with manual click-through work. If the search\n"
        "  returns zero hits, THEN fall back to the vendor URL via\n"
        "  mios-open-url and tell the operator winget didn't have it.\n"
        "- For 'close <X>' / 'quit <X>' / 'exit <X>' / 'stop <X>' where\n"
        "  X is an APP / GAME / WINDOW: the ONLY correct call is\n"
        "  `terminal: mios-window close \"<X>\"`. NEVER pkill, NEVER\n"
        "  taskkill /f, NEVER Stop-Process. WM_CLOSE lets the app save\n"
        "  state and exit cleanly; pkill loses unsaved work and -- if\n"
        "  the operator says 'close the crew' meaning the Crew Motorfest\n"
        "  game -- pkill might kill the WRONG process (an agent named\n"
        "  similarly, the OWUI gateway, hermes itself). Operator-flagged\n"
        "  2026-05-17: agent ran `pkill -f hermes-agent` thinking\n"
        "  'close the crew' meant 'close the agent crew' and gracefully\n"
        "  self-terminated. mios-window close on a title pattern\n"
        "  resolves the right hwnd from the live window list.\n"
        "- NEVER pkill / Stop-Process / systemctl stop any of these MiOS\n"
        "  services: hermes-agent, mios-open-webui, mios-delegation-\n"
        "  prefilter, mios-hermes-tail, hermes-dashboard, mios-daemon,\n"
        "  ollama. The operator runs MiOS through these; killing them\n"
        "  drops the conversation. For 'close hermes / restart hermes /\n"
        "  reset' use `terminal: mios-restart <svc>` (graceful).\n"
        "- NO FABRICATION for system state: dashboard / status / GPU /\n"
        "  disk / services / ollama questions MUST call mios-system-status\n"
        "  (via terminal). Never write hardware, service, or model\n"
        "  fields from training data.\n"
    )

    # ── Output polish system prompt ──
    # The output-refinement pass runs AFTER the agent dispatch (hermes
    # today; opencode / MCP / delegate children the same way) has
    # streamed its raw output. The raw output is preserved verbatim
    # inside a collapsed <details type="reasoning"> block; this polish
    # pass produces the operator-facing answer.
    #
    # Hard constraints (these are the failure modes from operator
    # chats 2026-05-17 we're closing):
    #  * RAW OUTPUT is ground truth. NEVER invent paths, IDs, numbers,
    #    statuses, app names, registry coords, port numbers, etc.
    #  * Strip narration. "Let me", "I'll", "First I...", "Now I'll"
    #    are agent thinking; the operator sees the polished answer
    #    only -- they don't need to read the agent's stream of
    #    consciousness.
    #  * If the agent failed, say what failed in ONE sentence + surface
    #    the verbatim error.
    #  * NO "would you like me to..." trailing questions unless the
    #    agent's raw output already proposed exactly that.
    #  * NO suggestions to "try X if Y" unless the agent surfaced X.
    _POLISH_SYSTEM = (
        "You are MiOS-Agent's FINAL-ANSWER polisher. The downstream\n"
        "agent (MiOS-Hermes today; same role for OpenCode / MCP /\n"
        "delegated subagents tomorrow) has just finished a task. Its\n"
        "RAW OUTPUT (narration, tool calls, intermediate text, final\n"
        "result) is provided below.\n"
        "\n"
        "Produce ONE clean operator-facing answer in markdown. The\n"
        "operator will not see the raw output, it's collapsed in a\n"
        "<details type=\"reasoning\"> block above your answer. They\n"
        "see only what you emit.\n"
        "\n"
        "## LOCALE\n"
        "Respond in the SAME language as the ORIGINAL OPERATOR ASK\n"
        "below. Mirror the operator's diction (formal vs casual,\n"
        "abbreviations, emoji usage). Never switch to English if the\n"
        "operator wrote in another language. Tool output (paths, IDs,\n"
        "command names, JSON keys) stays in its native form.\n"
        "\n"
        "## RULES (hard)\n"
        "- RAW OUTPUT is ground truth. NEVER invent paths, IDs,\n"
        "  numbers, statuses, app names, registry coords, ports, sizes,\n"
        "  timestamps, package names. If a field isn't in RAW OUTPUT,\n"
        "  don't write it.\n"
        "- Strip narration. Phrases like \"Let me\", \"I'll\", \"First\n"
        "  I...\", \"Now I'll\", \"Let me check\" are FORBIDDEN in your\n"
        "  output. The operator wants the result, not the reasoning.\n"
        "- Surface CONCRETE results: file paths, command exit codes,\n"
        "  app statuses, IDs, sizes, URLs -- straight from RAW OUTPUT.\n"
        "- If the agent FAILED, say what failed in ONE sentence and\n"
        "  surface the verbatim error in a code block.\n"
        "- NO \"would you like me to...\" trailing questions unless RAW\n"
        "  OUTPUT explicitly proposed exactly that.\n"
        "- NO \"if you'd like\" / \"feel free to\" / \"let me know if you\n"
        "  need\" boilerplate. End when the answer is done.\n"
        "- No preamble like \"Here's the result:\" -- get to the answer.\n"
        "- Use markdown tables / lists ONLY when they make the answer\n"
        "  clearer. A 1-line answer is one line.\n"
        "- Emit markdown SOURCE directly, NOT wrapped in ```markdown\n"
        "  ... ``` fences. OWUI renders bare markdown as proper markup\n"
        "  (headings, bold, lists, tables). Wrapping the WHOLE answer\n"
        "  in a code fence makes OWUI display the raw markdown source\n"
        "  inside a code block instead of rendering it. ONLY use code\n"
        "  fences for actual code / command snippets / shell output --\n"
        "  never for the framing of the answer itself.\n"
        "- If RAW OUTPUT is mostly empty / mostly tool calls with no\n"
        "  text result, summarize what tools ran + their outcomes in\n"
        "  one short paragraph. Never claim something worked that the\n"
        "  raw output doesn't confirm.\n"
        "\n"
        "## KNOWN AGENT ERRORS in RAW OUTPUT -- recognize + rewrite cleanly\n"
        "\n"
        "If RAW OUTPUT contains any of these signatures, DO NOT echo the\n"
        "raw error verbatim -- the operator already saw it once. Instead\n"
        "emit a single line explaining what the agent did wrong + what\n"
        "the operator should try next:\n"
        "\n"
        "  * `/var/lib/mios/hermes.<Word>` or `/var/lib/mios/hermes.<Prop>`\n"
        "    in any line that mentions 'not recognized' / 'cmdlet' / 'cannot\n"
        "    parse' -> The agent ran PowerShell syntax directly in `terminal:`\n"
        "    (bash). `$_` got mis-parsed as bash's last-arg variable.\n"
        "    Polished line:\n"
        "      'Agent attempted PowerShell in bash by mistake. Retry: the\n"
        "       request will be wrapped via `terminal: mios-windows ps`.'\n"
        "\n"
        "  * `screencapture.exe`, `Invoke-Screenshot`, `GDI+ error`, or\n"
        "    `cannot capture` errors -> The agent guessed at non-existent\n"
        "    screenshot tools instead of `mios-screenshot`. Polished line:\n"
        "      'Agent reached for an unavailable screenshot tool. Retry:\n"
        "       the canonical verb is `mios-screenshot [--open]`.'\n"
        "\n"
        "  * `Get-StartApps not found` / `pwsh not found` in bash output ->\n"
        "    Same PowerShell-in-bash pattern. Tell operator to retry; the\n"
        "    next attempt should use `mios-windows ps` or `mios-find`.\n"
        "\n"
        "  * `I don't have <tool> available` / `<tool> is not in my\n"
        "    toolset` claims about a tool that DOES ship (discord_send_\n"
        "    message, web_search, kanban_*, mios-* helpers) -> The agent\n"
        "    hallucinated the tool's absence. Polished line:\n"
        "      'Agent hallucinated that `<tool>` was unavailable. The tool\n"
        "       ships in the MiOS api_server toolset. Retry the request.'\n"
        "\n"
        "## ORIGINAL OPERATOR ASK\n"
        "{user_prompt}\n"
        "\n"
        "## RAW AGENT OUTPUT (ground truth)\n"
        "{raw_output}\n"
        "\n"
        "## POLISHED ANSWER\n"
    )

    # Cheap heuristic: if there's no narration marker AND the output
    # is short, skip the polish call entirely (saves 30-180s of CPU
    # for a result that's already clean).
    _NARRATION_MARKERS = re.compile(
        r"\b(let me|i.?ll|i'?ll|first,?\s*i|now,?\s*i|let.?s|i need to|i.?m going to|i.?ve|i.?m about to)\b",
        re.IGNORECASE,
    )

    def _looks_conversational(self, text: str) -> bool:
        if not text:
            return True
        if len(text.strip()) > 80:
            return False
        return bool(self._CONVERSATIONAL_RE.match(text.strip()))

    def _polish_can_skip(self, raw: str) -> bool:
        """Skip polish when raw is already short + clean."""
        if not raw:
            return True
        if len(raw) > int(self.valves.POLISH_SKIP_SHORT_CHARS):
            return False
        if self._NARRATION_MARKERS.search(raw):
            return False
        return True

    async def _polish_via_cpu(
        self,
        user_text: str,
        raw_output: str,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> str:
        """Output polish: takes raw agent output + original user prompt,
        returns the operator-facing answer. Falls back to raw on any
        failure (better than empty)."""
        if not self.valves.POLISH_ENABLED:
            return raw_output
        if not raw_output or not raw_output.strip():
            return raw_output
        if self._polish_can_skip(raw_output):
            await self._emit(emitter, "✓ short clean output -- skipping polish")
            return raw_output

        await self._emit(emitter, f"🎨 MiOS-Agent: polishing final answer via {self.valves.POLISH_MODEL} (CPU)...")

        body = {
            "model": self.valves.POLISH_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": self._POLISH_SYSTEM.format(
                        user_prompt=user_text[:2000],
                        raw_output=raw_output[:12000],
                    ),
                },
                {"role": "user", "content": "Emit the polished answer now."},
            ],
            "options": {
                "num_gpu": 0,
                "num_predict": int(self.valves.POLISH_MAX_TOKENS),
                "temperature": 0.0,
            },
            "keep_alive": -1,
            "stream": False,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=int(self.valves.POLISH_TIMEOUT_S))
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.valves.REFINE_ENDPOINT.rstrip("/") + "/api/chat",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status != 200:
                        await self._emit(emitter, f"⚠️ polish HTTP {resp.status} -- using raw")
                        return raw_output
                    data = await resp.json()
        except asyncio.TimeoutError:
            await self._emit(emitter, "⏱️  polish timeout -- using raw")
            return raw_output
        except Exception as e:
            await self._emit(emitter, f"⚠️ polish {type(e).__name__} -- using raw")
            return raw_output

        msg = (data.get("message") or {})
        polished = (msg.get("content") or msg.get("thinking") or "").strip()
        if not polished:
            await self._emit(emitter, "⚠️ polish returned empty -- using raw")
            return raw_output

        # Sanity check: if polish is suspiciously short vs raw, suspect
        # truncation; pass raw through with a one-line summary header.
        if len(polished) < min(40, len(raw_output) // 10):
            await self._emit(emitter, "⚠️ polish too short -- using raw")
            return raw_output

        # Strip the outer ```markdown ... ``` wrapper if the model
        # ignored the no-fence rule. The system prompt explicitly
        # forbids this but qwen2.5-coder:7b sometimes does it anyway,
        # and OWUI then renders the WHOLE answer as a code block
        # (operator-flagged 2026-05-17: every polished response was
        # showing as raw markdown source instead of rendered markup).
        polished = self._strip_outer_md_fence(polished)

        return polished

    _OUTER_FENCE_RE = re.compile(
        r"^\s*```(?:md|markdown|MD|MARKDOWN)?\s*\n(.*?)\n```\s*$",
        re.S,
    )

    def _strip_outer_md_fence(self, text: str) -> str:
        """If the entire response is wrapped in a ```markdown ... ```
        (or bare ```) fence, unwrap so OWUI renders the inner markdown
        as proper markup instead of as a code block."""
        m = self._OUTER_FENCE_RE.match(text)
        if not m:
            return text
        inner = m.group(1).strip()
        # Only unwrap if the inner content itself doesn't START with
        # a fence (preserves answers that genuinely lead with a code
        # block as their first element).
        if inner.startswith("```"):
            return text
        return inner

    async def _refine_via_cpu(
        self,
        user_text: str,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> str:
        """Call the small CPU refiner on Ollama. Returns refined text
        on success, or the ORIGINAL on failure / timeout / empty
        (best-effort -- the pipe is OWUI-facing so we never 503 here;
        worst case the unrefined prompt goes through)."""
        if not self.valves.REFINE_ENABLED or not user_text:
            return user_text
        if self.valves.REFINE_SKIP_SHORT and self._looks_conversational(user_text):
            await self._emit(emitter,
                f"💬 MiOS-Agent: conversational opener -- skipping refine")
            return user_text

        model = self.valves.REFINE_MODEL
        await self._emit(emitter,
            f"🧠 MiOS-Agent: refining via {model} (CPU)...")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._REFINE_SYSTEM},
                {"role": "user", "content": user_text},
            ],
            "options": {
                "num_gpu": 0,           # CPU per operator architecture
                "num_thread": 8,
                "num_predict": int(self.valves.REFINE_MAX_TOKENS),
                "temperature": 0.0,
            },
            "stream": False,
            "keep_alive": -1,           # always-on
        }
        url = self.valves.REFINE_ENDPOINT.rstrip("/") + "/api/chat"
        try:
            timeout = aiohttp.ClientTimeout(total=int(self.valves.REFINE_TIMEOUT_S))
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(url, data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"}) as r:
                    if r.status != 200:
                        await self._emit(emitter,
                            f"⚠️ refine: ollama {r.status} -- passing original")
                        return user_text
                    body = await r.json()
            msg = body.get("message") or {}
            refined = (msg.get("content") or "").strip()
            if not refined:
                # qwen3.5-family thinking-mode -- final answer empty,
                # thinking field has the trace. Use it but mark.
                refined = (msg.get("thinking") or msg.get("reasoning") or "").strip()
            if not refined:
                await self._emit(emitter,
                    "⚠️ refine: empty output -- passing original")
                return user_text
            await self._emit(emitter,
                f"✓ refined {len(user_text)}c -> {len(refined)}c (CPU)")
            return refined
        except asyncio.TimeoutError:
            await self._emit(emitter,
                f"⏱️  refine: timeout after {self.valves.REFINE_TIMEOUT_S}s -- passing original")
            return user_text
        except Exception as e:
            await self._emit(emitter,
                f"⚠️ refine: {type(e).__name__} -- passing original")
            return user_text

    async def _raw_passthrough(
        self,
        body: dict,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> AsyncGenerator[str, None]:
        """Stream the request straight through to hermes WITHOUT
        refinement, thinking-wrap, or polish. Used for OWUI's internal
        task-generation calls (title/tags/follow-up/autocomplete/etc.)
        that expect raw JSON or short labels back."""
        body = dict(body)
        body["model"] = self.valves.BACKEND_MODEL
        body["stream"] = True

        headers = {"Content-Type": "application/json"}
        if self.valves.BACKEND_KEY:
            headers["Authorization"] = f"Bearer {self.valves.BACKEND_KEY}"

        url = self.valves.BACKEND_URL.rstrip("/") + "/chat/completions"
        # Task-gen calls are short -- bound the timeout tighter than user chats.
        timeout = aiohttp.ClientTimeout(total=90, sock_connect=15, sock_read=None)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers,
                                        data=json.dumps(body).encode()) as resp:
                    if resp.status != 200:
                        err = (await resp.text())[:200]
                        await self._emit(emitter,
                            f"❌ task-gen backend {resp.status}", done=True)
                        yield ""    # OWUI tolerates empty for task-gen
                        return
                    async for raw_line in resp.content:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if not line or not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        delta = ((chunk.get("choices") or [{}])[0]
                                 .get("delta") or {})
                        piece = delta.get("content") or ""
                        if piece:
                            yield piece
            await self._emit(emitter, "✅ task-gen done", done=True)
        except asyncio.TimeoutError:
            await self._emit(emitter, "⏱️  task-gen timeout", done=True)
            yield ""
        except Exception as e:
            await self._emit(emitter,
                f"❌ task-gen {type(e).__name__}: {e}", done=True)
            yield ""

    def _process_buffer(self, buffer: str) -> tuple[str, str]:
        """Pop COMPLETED lines from buffer, transform, return (yieldable, leftover).
        Narration lines get <think>...</think> wrapping; final-answer lines pass through.
        Adjacent narration coalesces into a single <think> block."""
        if not self.valves.COLLAPSE_NARRATION:
            return buffer, ""
        # Only process up to the last newline; anything after stays buffered.
        if "\n" not in buffer:
            return "", buffer
        head, _, tail = buffer.rpartition("\n")
        # head already excludes the trailing newline; restore it for splitlines.
        out_parts: list[str] = []
        narration_run: list[str] = []

        def _flush_narration():
            if narration_run:
                joined = "\n".join(narration_run).rstrip()
                out_parts.append(f"<think>{joined}</think>\n")
                narration_run.clear()

        for line in head.splitlines():
            if _is_narration_line(line):
                narration_run.append(line)
            else:
                _flush_narration()
                out_parts.append(line + "\n")
        _flush_narration()
        return "".join(out_parts), tail

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[..., Awaitable[None]]] = None,
        __metadata__: Optional[dict] = None,
        __task__: Optional[str] = None,
        __tools__: Optional[list] = None,
        __files__: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        # ── Task-generation bypass (OWUI internal calls) ─────────────
        # OWUI calls the same model for title / tags / follow-up /
        # autocomplete / query / image-prompt generation. These calls
        # come WITH __task__ set + expect raw JSON or short labels back
        # (NOT refined, NOT wrapped in <details>, NOT polished into
        # markdown). Running them through refinement+polish strips the
        # JSON the followup template asks for -- which is why
        # ENABLE_FOLLOW_UP_GENERATION=True yields no followups in OWUI
        # (operator-flagged 2026-05-17). Detect + passthrough.
        task_kind = (__task__ or "").strip().lower()
        if not task_kind and isinstance(__metadata__, dict):
            # Some OWUI versions stash task in metadata.task instead of __task__
            task_kind = str(__metadata__.get("task") or "").strip().lower()
        is_task_gen = task_kind in {
            "title_generation", "tags_generation", "follow_up_generation",
            "autocomplete_generation", "query_generation", "image_prompt_generation",
            "moa_response_generation", "function_calling",
        }

        if is_task_gen:
            await self._emit(__event_emitter__,
                f"⚙️  task-gen ({task_kind}): bypassing refine + polish")
            async for chunk in self._raw_passthrough(body, __event_emitter__):
                yield chunk
            return

        await self._emit(__event_emitter__, "📡 MiOS-Agent: receiving prompt...")

        body = dict(body)
        body["model"] = self.valves.BACKEND_MODEL
        body["stream"] = True

        # ── CPU REFINEMENT (in-pipe) ─────────────────────────────────
        # Extract the last user message, refine via the small CPU model,
        # replace the user message in-place with the refined text. The
        # downstream chain (prefilter -> hermes) sees the enriched
        # prompt, not the raw input.
        messages = body.get("messages") or []
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], dict) and messages[i].get("role") == "user":
                last_user_idx = i
                break
        if last_user_idx >= 0:
            raw = messages[last_user_idx].get("content") or ""
            # OpenAI multi-part content shape: pick the first text segment
            if isinstance(raw, list):
                for part in raw:
                    if isinstance(part, dict) and part.get("type") == "text":
                        raw = part.get("text", "")
                        break
                else:
                    raw = ""
            if isinstance(raw, str) and raw.strip():
                refined = await self._refine_via_cpu(raw, __event_emitter__)
                if refined and refined != raw:
                    # Write back as a plain string (downstream tolerates both)
                    messages[last_user_idx]["content"] = refined
                    body["messages"] = messages

        headers = {"Content-Type": "application/json"}
        if self.valves.BACKEND_KEY:
            headers["Authorization"] = f"Bearer {self.valves.BACKEND_KEY}"

        await self._emit(__event_emitter__, "🧠 MiOS-Agent: dispatching to hermes...")

        # Unbounded sock_read (LLM stream can idle 10s+ between chunks on
        # CPU); only sock_connect bounded so we don't hang if the backend
        # is down. TIMEOUT_S=0 => unbounded total.
        total = None if self.valves.TIMEOUT_S <= 0 else self.valves.TIMEOUT_S
        timeout = aiohttp.ClientTimeout(total=total, sock_connect=15, sock_read=None)
        url = self.valves.BACKEND_URL.rstrip("/") + "/chat/completions"

        stop_tail = asyncio.Event()
        tail_task = asyncio.create_task(self._tail_watcher(__event_emitter__, stop_tail))

        # ── ALL agent dispatch output is captured + wrapped as
        # collapsible <details type="reasoning">. After the stream
        # ends, the polish pass emits the operator-facing answer.
        # Operator architecture 2026-05-17: "ALL MiOS-Agent(OWUI)'s
        # dispatches (MiOS-Hermes, MiOS-OpenCode, etc) are always
        # capturing their outputs as thinking and providing an
        # appropriate final answer normally in OWUI chats".
        raw_buffer = ""
        any_text = False

        # Open the collapsible thinking block. OWUI renders
        # <details type="reasoning"> as a click-to-expand row above the
        # assistant message. The streaming chunks land INSIDE so the
        # operator can watch it tick in real time if they expand it.
        if self.valves.POLISH_ENABLED:
            yield (
                f"<details type=\"reasoning\" data-mios-agent=\"hermes\">\n"
                f"<summary>{self.valves.AGENT_THINKING_LABEL}</summary>\n\n"
            )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers,
                                        data=json.dumps(body).encode()) as resp:
                    if resp.status != 200:
                        err = (await resp.text())[:300]
                        if self.valves.POLISH_ENABLED:
                            yield "</details>\n\n"
                        await self._emit(__event_emitter__,
                                         f"❌ backend {resp.status}: {err}",
                                         done=True)
                        yield f"backend error {resp.status}: {err}"
                        return

                    async for raw_line in resp.content:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if not line or not line.startswith("data:"):
                            continue
                        payload_str = line[5:].strip()
                        if payload_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = (choices[0].get("delta") or {})
                        text_piece = delta.get("content") or ""
                        if not text_piece:
                            continue
                        any_text = True
                        raw_buffer += text_piece
                        # Stream into the details block AS IT ARRIVES so
                        # the expand-while-streaming UX still works.
                        yield text_piece

            # Close the thinking block before polish so the polished
            # answer renders below it as the visible assistant message.
            if self.valves.POLISH_ENABLED:
                yield "\n</details>\n\n"

            raw_text = raw_buffer.strip()

            if not any_text or not raw_text:
                yield "_(MiOS-Agent: backend returned no content)_"
                await self._emit(__event_emitter__, "✅ MiOS-Agent: done", done=True)
                return

            # If polish is OFF, the legacy flow already emitted text
            # via yield above; nothing more to do.
            if not self.valves.POLISH_ENABLED:
                await self._emit(__event_emitter__, "✅ MiOS-Agent: done", done=True)
                return

            # Polish: CPU pass to clean narration + surface concrete
            # results. Falls back to raw on any error.
            user_text_for_polish = ""
            try:
                last_user = next(
                    (m.get("content") or "") for m in reversed(messages)
                    if isinstance(m, dict) and m.get("role") == "user"
                )
                user_text_for_polish = last_user if isinstance(last_user, str) else ""
            except StopIteration:
                pass

            polished = await self._polish_via_cpu(
                user_text_for_polish, raw_text, __event_emitter__,
            )
            yield polished

            await self._emit(__event_emitter__, "✅ MiOS-Agent: done", done=True)
        except asyncio.TimeoutError:
            # Close the <details> if we opened one, otherwise OWUI
            # renders the rest of the message as collapsed-reasoning.
            if self.valves.POLISH_ENABLED:
                yield "\n</details>\n\n"
            await self._emit(__event_emitter__,
                             f"⏱️  timeout after {self.valves.TIMEOUT_S}s",
                             done=True)
            yield f"\n\n_(MiOS-Agent: backend timed out)_"
        except Exception as e:
            if self.valves.POLISH_ENABLED:
                yield "\n</details>\n\n"
            await self._emit(__event_emitter__,
                             f"❌ pipe error: {type(e).__name__}: {e}",
                             done=True)
            yield f"\n\n_(MiOS-Agent: pipe error: {type(e).__name__}: {e})_"
        finally:
            stop_tail.set()
            try:
                await asyncio.wait_for(tail_task, timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                pass

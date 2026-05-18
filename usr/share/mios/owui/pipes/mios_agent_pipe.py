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
            description="Emit status events (🧠 refine, 🧠 → hermes, 🛠️ tool, 🎨 polish, ✅). Symbol+term form, locale-neutral.",
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
        # ── Phase-2 Critic loop (see docs/multi-agent-architecture.md)
        # The Critic Agent reviews the compose draft against the
        # structured tool history. If the draft claims success on a
        # tool that failed, claims a step ran when no tool_call for
        # it exists, or otherwise mismatches the structured truth,
        # critic returns issues; compose revises once. Bounded loop.
        CRITIC_ENABLED: bool = Field(
            default=True,
            description="After compose drafts an answer, run a small Critic Agent that reviews against the structured tool history. Catches false-success claims, missing steps, fabrications -- replaces the hardcoded KNOWN_AGENT_ERROR_RE rewrite path with a natural multi-agent reflexion loop.",
        )
        CRITIC_MODEL: str = Field(
            default="qwen3:1.7b",
            description="Small model for the critic pass. Per operator directive 2026-05-17 'iGPU's are ONLY micro-llms' -- micro-LLMs land on the AMD/Intel iGPU CDI lane when present, leaving the dGPU free for big-model work. qwen3:1.7b ~1.4 GB.",
        )
        CRITIC_TIMEOUT_S: int = Field(
            default=45,
            description="Cap the critic call. Small model + structured input + JSON-only output = sub-10s typical; 45s is the safety ceiling.",
        )
        CRITIC_MAX_TOKENS: int = Field(
            default=300,
            description="Cap critic output. JSON verdict + issue list fits comfortably.",
        )
        CRITIC_MAX_ITERATIONS: int = Field(
            default=1,
            description="Max revise cycles. 0 = run critic but never revise (audit-only). 1 = one revision pass (compose, critique, revise, done). Bounded reflexion -- never infinite loop.",
        )
        AGENT_THINKING_LABEL: str = Field(
            default="🧠 MiOS-Hermes",
            description="The <summary> rendered above the collapsed reasoning block. Per-agent label so the operator can tell which agent (hermes / opencode / etc.) produced the thinking. Kept short + symbol-led so it reads the same across operator locales (operator directive 2026-05-17 GLOBAL SWEEP for hardcoded English).",
        )

    # Operator directive 2026-05-17: "prompt refining should be tool
    # aware to be able to hint". The refine system prompt has a
    # {tool_table} placeholder filled at init from the YAML manifest
    # at /usr/share/mios/owui/tool-hints.yaml. Adding a new shim =
    # one YAML entry, no prompt rewrite.
    _TOOL_HINTS_PATH = "/usr/share/mios/owui/tool-hints.yaml"

    def __init__(self):
        self.valves = self.Valves()
        self.name = "MiOS-Agent"
        # Build the tool table once at init; pipe restart picks up
        # YAML edits.
        self._refine_system_rendered = self._render_refine_system()

    def _render_refine_system(self) -> str:
        """Load tool-hints.yaml, render the canonical-verbs section as
        a markdown table, and substitute into _REFINE_SYSTEM. Falls
        back to the un-substituted prompt on any error (YAML missing,
        parse error, etc.) so the refine pass still runs."""
        try:
            import yaml as _yaml
            with open(self._TOOL_HINTS_PATH, "r", encoding="utf-8") as f:
                manifest = _yaml.safe_load(f) or {}
        except Exception:
            # Inject a noop placeholder so .format() doesn't KeyError.
            return self._REFINE_SYSTEM.replace(
                "{tool_table}",
                "(tool-hints.yaml not loaded -- agent must rely on PATH discovery)",
            )
        verbs = manifest.get("canonical_verbs") or []
        if not verbs:
            return self._REFINE_SYSTEM.replace(
                "{tool_table}", "(no canonical verbs registered)",
            )
        # Compact markdown table: name | intent | example. Three
        # columns keeps each row scannable; the model uses the
        # 'intent' column to match the user's ask.
        rows = ["| Verb | Intent | Example |", "|------|--------|---------|"]
        for v in verbs:
            name = v.get("name", "?")
            intent = (v.get("intent", "") or "").replace("|", "\\|")
            example = (v.get("example", "") or "").replace("|", "\\|")
            rows.append(f"| `{name}` | {intent} | `{example}` |")
        # Optional intent_patterns block -- per-pattern hints for
        # composite asks the verb table alone doesn't cover.
        patterns = manifest.get("intent_patterns") or []
        extras = []
        if patterns:
            extras.append("")
            extras.append("Intent patterns (for asks the verb table alone misses):")
            for p in patterns:
                m = p.get("match", "?")
                c = p.get("first_call", "")
                n = p.get("note", "")
                extras.append(f"- `{m}` → `{c}`  ({n})" if n else
                              f"- `{m}` → `{c}`")
        table = "\n".join(rows + extras)
        return self._REFINE_SYSTEM.replace("{tool_table}", table)

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
    # Operator directive 2026-05-17: GLOBAL SWEEP to remove hardcoded
    # English. The conversational gate now matches greetings/acks/
    # farewells across the languages the operator's chats commonly
    # use. New languages can be added without code review by editing
    # the alternation. The bare-name list (hi, hola, etc.) covers
    # standalone tokens; the phrase list covers multi-word openers.
    _CONVERSATIONAL_RE = re.compile(
        # English / generic. The "X there"/"X y'all"/"X everyone"
        # forms (Hey there!, Hi y'all, Hello everyone) are bundled
        # in the leading-word alternation so they also short-circuit
        # to skip-refine. Operator-flagged 2026-05-18: "Hey there!"
        # was inflating from 10c to 111c via refine because the
        # 1-word gate failed to match.
        r"^\s*((?:hi|hello|hey|yo|howdy)(?:\s+(?:there|y[’']?all|everyone|all|guys|friend|friends|bot))?|"
        r"sup|gm|gn|ok|okay|kk|alright|"
        r"thanks|thx|ty|thank you|cool|nice|great|got it|"
        r"sounds good|sgtm|sure|yes|no|yep|nope|yeah|nah|"
        r"bye|cya|goodbye|later|peace|seeya|"
        r"good (morning|afternoon|evening|night)|"
        r"what[’']?s (up|new|good|happening|going on)|"
        r"how['’]?s (it going|things|things today|things going|life|stuff)|"
        r"how (are|have|you been|are things|are you|are ya|"
        r"you doing|you been|is it going|is everything)|"
        r"what do you (want|wanna|got|need)|"
        # Spanish / Portuguese
        r"hola|holi|holaaa+|buenas|buenos d[ií]as|buenas (tardes|noches)|"
        r"gracias|de nada|adi[óo]s|chao|chau|hasta luego|qu[eé] tal|"
        r"c[óo]mo (est[áa]s|va|andas)|todo bien|vale|s[íi]|"
        r"ol[áa]|bom dia|boa (tarde|noite)|obrigad[oa]|tudo bem|tchau|"
        # French
        r"salut|bonjour|bonsoir|bonne nuit|merci|merci beaucoup|"
        r"de rien|au revoir|[àa] bient[oô]t|[çc]a va|comment [çc]a va|d[’']accord|oui|non|"
        # Italian
        r"ciao|salve|buongiorno|buonasera|buonanotte|"
        r"grazie|prego|arrivederci|come stai|come va|s[íi]|"
        # German / Dutch / Nordics
        r"hallo|hi+|moin|servus|gr[üu][sß] (dich|gott)|guten (morgen|tag|abend)|"
        r"danke|bitte|tsch[üu]ss|auf wiedersehen|wie geht.?s|"
        r"hej|hej hej|hejs[åa]|tack|farv[ée]l|"
        r"hallo|hoi|dag|dankjewel|doei|"
        # Slavic (Latin transliteration tolerated; native scripts below)
        r"czesc|cze[śs][ćc]|dzi[ęe]kuj[ęe]|do widzenia|"
        r"ahoj|d[ěe]kuji|d[ěe]k|nashledanou|"
        # Asian (Latin)
        r"ohayou?|konnichiwa|konbanwa|sayounara|arigatou?|"
        r"annyeong(haseyo)?|kamsahamnida|"
        r"ni hao|xie ?xie|zai ?jian|"
        # Other / multilingual
        r"namaste|namaskar|shukriya|dhanyavaad|"
        r"shalom|toda|"
        r"mahalo|aloha)[!?.,\s]*$"
        # Native-script openers (single-line)
        r"|^\s*(?:привет|здравствуй(те)?|спасибо|пока|до свидания)[!?.,\s]*$"
        r"|^\s*(?:你好|您好|嗨|哈罗|谢谢|再见)[!?.,\s]*$"
        r"|^\s*(?:こんにちは|こんばんは|おはよう(ございます)?|ありがとう(ございます)?|さようなら|またね)[!?.,\s]*$"
        r"|^\s*(?:안녕(하세요)?|반갑습니다|감사합니다|고마워(요)?|잘 ?가)[!?.,\s]*$"
        r"|^\s*(?:مرحبا|أهلا|السلام عليكم|شكرا|وداعا)[!?.,\s]*$"
        r"|^\s*(?:שלום|תודה|להתראות)[!?.,\s]*$",
        re.IGNORECASE,
    )

    # Refine system prompt — OpenAI-API-standard format (operator
    # directive 2026-05-17: "simplify to OpenAI API standards for
    # Day-0 Agents understanding -- Do a pass on ALL system prompts").
    # Tool-aware: the {tool_table} placeholder is filled at runtime
    # from /usr/share/mios/owui/tool-hints.yaml so adding a new shim
    # = one YAML entry, no prompt edits ("prompt refining should be
    # tool aware to be able to hint" -- same operator turn).
    #
    # Goal: a fresh agent reads this and groks the pattern in 30
    # seconds. Role + output schema + tool table + ~5 hard rules + 4
    # high-signal examples covering the failure modes that recur
    # (launch / image / map / Linux-GUI / "near <place>").
    _REFINE_SYSTEM = (
        # Generic OpenAI-style refinement layer prompt -- operator
        # directive 2026-05-17: "generisize this to be completely
        # platform agnostic and plain generic english (or standard
        # OpenAI patterns here)". Platform-specific facts live in
        # the {tool_table} injected from tool-hints.yaml; rules are
        # phrased generically (no host names, no distro, no
        # operator handle).
        "You are a prompt refinement layer for a multi-agent system.\n"
        "Rewrite the user's raw request into a structured handoff the\n"
        "downstream orchestrator agent will execute.\n"
        "\n"
        "## THINK FIRST, then emit the structured handoff\n"
        "Before writing the schema below, reason step-by-step in a\n"
        "single THINKING block: (a) restate the user's intent in one\n"
        "phrase, (b) scan the canonical-verbs table for the row that\n"
        "matches, (c) decide if the intent is single-step or multi-\n"
        "step, (d) decide if delegate fan-out helps. Keep THINKING\n"
        "under 80 tokens. Mirror the user's language.\n"
        "\n"
        "## OUTPUT SCHEMA (emit EXACTLY this, nothing else)\n"
        "THINKING: <free-form planning, <=80 tokens>\n"
        "INTENT: <one sentence: what the user wants>\n"
        "TOOLS: <comma-separated downstream tool names>\n"
        "DELEGATE: <YES if parallel fan-out is sensible, else NO>\n"
        "PLAN:\n"
        "  1. <tool>: <exact command / arguments>\n"
        "  2. ...\n"
        "\n"
        "## CANONICAL VERBS (PREFER these over generic shells; pick the row matching the user's intent)\n"
        "{tool_table}\n"
        "\n"
        "## DOWNSTREAM TOOLS (available to the orchestrator)\n"
        "terminal (any shell command, including the verbs above),\n"
        "delegate_task (spawn parallel sub-agents), web_search,\n"
        "web_extract (SEARCH-ONLY backend -- never expect URL content\n"
        "back; for URL content use `terminal: curl ...`),\n"
        "discord_send_message, cronjob_*, kanban_*, memory_*, read_file,\n"
        "write_file, skill_view, skill_manage.\n"
        "\n"
        "browser_* (browser_navigate, browser_console, browser_snapshot,\n"
        "browser_click, browser_type) drives a HEADLESS CDP session the\n"
        "user CANNOT see -- only useful for scraping or inspection. For\n"
        "any user-visible browser action prefer the canonical verbs above\n"
        "(URL open / map / image). Before ANY browser_* call, the agent\n"
        "must run the canonical 'bring CDP up' verb first.\n"
        "\n"
        "## HARD RULES\n"
        "- Trivial intent (matches ONE canonical-verb row) → ONE PLAN\n"
        "  line. No padding, no skill loads, no web_extract noise.\n"
        "- EXECUTE a launcher's resolved target verbatim. Never\n"
        "  substitute a different launcher (e.g. if the launcher\n"
        "  returned a vendor URI, do NOT switch to a different\n"
        "  storefront).\n"
        "- '<query> near <PLACE>' / 'around <PLACE>' / 'by <PLACE>':\n"
        "  resolve the PLACE'S ADDRESS first (canonical 'map' verb),\n"
        "  then web_search anchored on that address. Never return\n"
        "  generic same-city results.\n"
        "- 'open <url>', 'go to <url>', 'show me a map of', 'directions\n"
        "  to', 'show a picture of', 'open <gui-app>' all map to specific\n"
        "  canonical verbs above. NEVER claim the environment 'cannot\n"
        "  display' or 'cannot open a browser' -- if a canonical verb\n"
        "  exists for the intent, USE IT.\n"
        "- 'close <X>' (app/game/window): use the canonical close\n"
        "  verb (graceful WM_CLOSE). NEVER pkill / Stop-Process /\n"
        "  systemctl stop on infrastructure services.\n"
        "- Output ONLY the labeled INTENT/TOOLS/DELEGATE/PLAN block.\n"
        "  No preamble, no markdown headers (no ##), no commentary,\n"
        "  no closing remarks.\n"
        "- Stay under 300 tokens total.\n"
        "\n"
        "## EXAMPLES (4 high-signal cases)\n"
        "\n"
        "USER: launch the crew motorfest\n"
        "INTENT: Launch The Crew Motorfest on the user's screen.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-find \"the crew motorfest\" | bash\n"
        "  2. terminal: mios-window-active --present \"Crew Motorfest\"\n"
        "\n"
        "USER: show me a picture of a cute dog on the left of my screen\n"
        "INTENT: Open an image of a cute dog in the browser, positioned left.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-show-image \"cute dog\" --position left\n"
        "\n"
        "USER: what restaurants are near Anime North in Toronto\n"
        "INTENT: List restaurants near the Anime North venue (Toronto Congress Centre, 650 Dixon Rd).\n"
        "TOOLS: terminal, web_search\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-map \"Toronto Congress Centre 650 Dixon Rd\"\n"
        "  2. web_search \"restaurants near 650 Dixon Road Toronto\"\n"
        "\n"
        "USER: open gnome settings on my pc\n"
        "INTENT: Open GNOME Control Center on the user's screen.\n"
        "TOOLS: terminal\n"
        "DELEGATE: NO\n"
        "PLAN:\n"
        "  1. terminal: mios-gui-launch gnome-control-center\n"
        "  2. terminal: mios-window-active --present \"Settings\"\n"
    )

    # (the prior 200-line refine prompt -- intent table, fixated
    # examples, MiOS-specific preamble -- is now deleted; replaced
    # by the OpenAI-standard prompt above + tool-hints.yaml injection
    # at runtime. Operator directives 2026-05-17: "simplify to OpenAI
    # API standards for Day-0 Agents understanding -- Do a pass on
    # ALL system prompts" + "generisize this to be completely platform
    # agnostic and plain generic english (or standard OpenAI patterns
    # here)" + "ABSOLUTELY NO HARDCODED ENGLISH STANDARD Linux and
    # Windows Terminologies".)
    _LEGACY_REFINE_DELETED = True

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
        "- NEVER report an action as 'successful' / 'completed' / 'opened' /\n"
        "  'launched' / 'posted' / 'sent' unless RAW OUTPUT contains the\n"
        "  matching tool_result with success:true. Operator-flagged\n"
        "  2026-05-18: polish claimed 'Open YouTube: Successfully opened\n"
        "  YouTube' + 'Web Search: Proceeded with the web search' when\n"
        "  only one (failing) web_extract call had actually run. Reporting\n"
        "  steps that did NOT execute is a defect. If a planned step did\n"
        "  not run or did not succeed, SAY SO -- 'Step 2 (web_search) did\n"
        "  not run' or 'Step 1 (mios-open-url) returned exit 1: <err>'.\n"
        "- NEVER emit <details> in your output. The pipe wraps agent\n"
        "  thinking in its own <details type=\"reasoning\"> block above\n"
        "  your answer. Adding another one stacks them and the operator\n"
        "  sees two expand-arrows. Plain markdown only.\n"
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
        "- NO inventing operator-state: 'I appreciate the kind words',\n"
        "  'thanks for the patience', 'just to keep things clear I'm\n"
        "  actually running model X' -- the operator did NOT say kind\n"
        "  words, did NOT ask about your model, did NOT thank you.\n"
        "  Polish the RESULT, not a parasocial chat. If RAW OUTPUT\n"
        "  contains this kind of preamble, DELETE it -- don't pass\n"
        "  it through.\n"
        "- NO offering alternatives the agent didn't actually try.\n"
        "  'I can generate a text description', 'I can find images\n"
        "  online for you' -- if the action wasn't run, don't pitch\n"
        "  it as a follow-up. The operator wants the thing they\n"
        "  asked for, OR a clear single-sentence reason it didn't\n"
        "  happen + the fix to retry.\n"
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
        "IMPORTANT: only apply the rewrites below when the raw output\n"
        "does NOT also contain a confirmed-success signal -- specifically\n"
        "a tool_result with `success: true`, a `pid: <N>` in broker\n"
        "output, a `presented_to_operator: true` from mios-window-active,\n"
        "or a `wrote <path>` line from a file/CDI helper. If the agent\n"
        "errored during exploration but ultimately succeeded, polish\n"
        "the SUCCESS not the error -- operator-flagged 2026-05-18:\n"
        "polish rewrote a successful Notepad launch (pid 499978) into\n"
        "'Agent attempted PowerShell in bash by mistake' because an\n"
        "earlier exploratory bash call in the same turn errored. The\n"
        "operator saw a misleading failure message for what was\n"
        "actually a working launch (the broker had a separate\n"
        "invisible-window bug fixed in mios-windows; the polish\n"
        "false-positive compounded it).\n"
        "\n"
        "If RAW OUTPUT contains any of these signatures AND no\n"
        "confirmed-success signal, DO NOT echo the raw error verbatim --\n"
        "the operator already saw it once. Instead emit a single line\n"
        "explaining what the agent did wrong + what the operator\n"
        "should try next:\n"
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
        "    toolset` / `appears to be vendor-specific` / `not in\n"
        "    this environment` claims about anything starting with\n"
        "    `mios-` (a SHELL helper on PATH) or the native gateway\n"
        "    tools (discord_send_message, web_search, kanban_*,\n"
        "    delegate_task, memory_save, etc.) -> The agent\n"
        "    hallucinated the tool's absence. The fix is one shell\n"
        "    call. Polished line:\n"
        "      'Agent hallucinated that `<tool>` was unavailable. For\n"
        "       any `mios-*` verb, run `terminal: <tool> <args>` --\n"
        "       it lives on $PATH. Native gateway tools live in the\n"
        "       MiOS api_server toolset. Retry the request.'\n"
        "\n"
        "  * `no display server` / `no active X server` / `no X server\n"
        "    or Wayland` / `terminal restrictions prevent running\n"
        "    graphical apps` / `display infrastructure issue` / `pure\n"
        "    terminal service` / `browser can't launch in this\n"
        "    environment` -> ALL LIES. MiOS WSL2 has WSLg (DISPLAY=:0,\n"
        "    WAYLAND_DISPLAY=wayland-0, /mnt/wslg/ mounted). The agent\n"
        "    forgot to use the canonical shim. Polished line:\n"
        "      'Agent skipped the canonical WSLg launcher. Retry with\n"
        "       `terminal: mios-gui-launch <app>` for Linux GUI apps\n"
        "       or `terminal: mios-open-url <url>` for browser opens\n"
        "       -- both work in this MiOS environment.'\n"
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
    # "Looks like structured markdown" -- a heading line OR a markdown
    # table separator (`|---|`). When raw output starts with one of
    # these, hermes is already shaping the answer; polish has nothing
    # to add and a non-trivial chance of mangling it.
    _STRUCTURED_MD_RE = re.compile(
        r"^\s*(?:#{1,6}\s+\S|\|[\s\-:|]+\|)",
        re.M,
    )
    # Known agent-error signatures: if the raw output contains these,
    # ALWAYS polish (so the "KNOWN AGENT ERRORS" rewrites in the polish
    # prompt have a chance to clean them up).
    _KNOWN_AGENT_ERROR_RE = re.compile(
        r"(?:not recognized|cmdlet|cannot parse|screencapture\.exe|"
        r"Invoke-Screenshot|GDI\+|Get-StartApps not found|pwsh not found|"
        r"vendor-specific|I don.t have|not in (?:my toolset|this environment)|"
        # WSLg gaslighting (operator-flagged 2026-05-17 after agent ran 6 calls
        # then claimed all three of these to refuse opening gnome-control-center)
        r"no (?:active )?(?:X server|display server|X server or Wayland)|"
        r"terminal restrictions prevent|display infrastructure issue|"
        r"pure terminal service|browser can.t launch in this environment|"
        r"can.t open a map for you in this WSL environment)",
        re.IGNORECASE,
    )

    # Native multi-agent compose -- structured handoff from Hermes
    # session JSON (operator directive 2026-05-18: "HOW WOULD THIS
    # MULTI_AGENTIC_REASONING WORK NATIVELY!??? RESEARCH!" + "make
    # sure this is ALL ALSO OpenAI API COMPLIANT and COMPLETELY
    # FUnctional on a Bootc Bootable OCI MiOS image").
    #
    # Architecture (see /usr/share/mios/docs/multi-agent-architecture.md
    # for the full research + migration plan):
    #   Phase 1 (this code): Compose reads Hermes session JSON for
    #     the OpenAI-format tool_calls + tool_result message history,
    #     reasons over STRUCTURE instead of text-mangled stream.
    #   Phase 2 (future):    Add explicit Critic Agent loop on
    #     iGPU micro-LLM (qwen3:1.7b).
    #   Phase 3 (future):    Refine emits JSON {intent, plan} rather
    #     than INTENT/TOOLS/DELEGATE/PLAN labels.
    #   Phase 4 (future):    Drop regex post-processors (think /
    #     details strip, KNOWN_AGENT_ERROR_RE, etc.).
    #
    # OpenAI compliance: the tool_call + tool_result shape is the
    # standard OpenAI Chat Completions message format. Hermes
    # records exactly this in session JSON; we surface it untouched
    # to the compose model. Any OpenAI-API-compatible model
    # (Claude, GPT-*, local Ollama) can consume the structured
    # input identically.
    HERMES_SESSIONS_DIR = "/var/lib/mios/hermes/sessions"

    def _load_session_tool_history(self, after_ts: float,
                                    max_age_s: float = 600
                                    ) -> Optional[list[dict]]:
        """Find the newest Hermes session JSON whose mtime is later
        than `after_ts` (the moment the pipe dispatched to hermes)
        and within `max_age_s` of now. Return the OpenAI-format
        message list (user/assistant/tool) for the compose layer.
        Returns None when no session found or unreadable -- compose
        falls back to the legacy text-blob path.

        Day-0 / bootc note: HERMES_SESSIONS_DIR lives under
        /var/lib/mios/hermes (created by mios-hermes-firstboot at
        first boot; bootc-bootable). No /etc writes required."""
        import glob, os, json as _json
        try:
            sessions = sorted(
                glob.glob(f"{self.HERMES_SESSIONS_DIR}/session_*.json"),
                key=os.path.getmtime, reverse=True,
            )
        except OSError:
            return None
        now = time.time()
        for path in sessions[:5]:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime < after_ts:
                # Older than the dispatch -- not this turn's session.
                break
            if (now - mtime) > max_age_s:
                continue
            try:
                d = _json.loads(open(path, "r", encoding="utf-8").read())
            except (OSError, _json.JSONDecodeError):
                continue
            msgs = d.get("messages") or []
            if not msgs:
                continue
            # Keep only the operator-relevant slice: the LAST
            # user-message and every message after it.
            last_user_idx = -1
            for i in range(len(msgs) - 1, -1, -1):
                m = msgs[i]
                if isinstance(m, dict) and m.get("role") == "user":
                    last_user_idx = i; break
            slice_msgs = msgs[last_user_idx:] if last_user_idx >= 0 else msgs
            return slice_msgs
        return None

    def _render_tool_history_for_compose(self, msgs: list[dict]) -> str:
        """Render the OpenAI-format message list as a compact JSON
        the compose model can reason over. Pairs each assistant
        tool_call with its matching tool_result message and adds a
        derived `success` field (parsed from the tool result content
        when the upstream tool returned JSON with `success` -- the
        MiOS verb convention)."""
        import json as _json
        # Build call-id -> result-content index
        results: dict[str, dict] = {}
        for m in msgs:
            if not isinstance(m, dict) or m.get("role") != "tool":
                continue
            tcid = m.get("tool_call_id") or ""
            content = m.get("content") or ""
            success: Optional[bool] = None
            try:
                parsed = _json.loads(content) if isinstance(content, str) else None
                if isinstance(parsed, dict) and "success" in parsed:
                    success = bool(parsed["success"])
            except (_json.JSONDecodeError, ValueError):
                pass
            # Trim noisy content for the compose prompt.
            preview = content if isinstance(content, str) else str(content)
            results[tcid] = {
                "tool_call_id": tcid,
                "content_preview": preview[:1200],
                "success": success,
            }
        events: list[dict] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            if role == "user":
                events.append({
                    "role": "user",
                    "content": (m.get("content") or "")[:1200],
                })
            elif role == "assistant":
                tc = m.get("tool_calls") or []
                if tc:
                    for t in tc:
                        fn = (t.get("function") or {}) if isinstance(t, dict) else {}
                        name = fn.get("name", "?")
                        args = fn.get("arguments", "")
                        tcid = t.get("id", "") if isinstance(t, dict) else ""
                        r = results.get(tcid, {})
                        events.append({
                            "role": "assistant.tool_call",
                            "tool_call_id": tcid,
                            "tool": name,
                            "arguments": args[:600] if isinstance(args, str)
                                         else _json.dumps(args)[:600],
                            "success": r.get("success"),
                            "result_preview": r.get("content_preview", ""),
                        })
                text = m.get("content")
                if text:
                    events.append({
                        "role": "assistant.text",
                        "content": str(text)[:1200],
                    })
        return _json.dumps({"history": events}, indent=2)

    def _looks_conversational(self, text: str) -> bool:
        if not text:
            return True
        if len(text.strip()) > 80:
            return False
        return bool(self._CONVERSATIONAL_RE.match(text.strip()))

    def _polish_can_skip(self, raw: str) -> bool:
        """Skip polish when raw is already a clean operator-facing answer.

        Skip if EITHER:
          a) Short + no narration markers (the original heuristic), OR
          b) Looks like structured markdown (heading or table block) +
             no narration markers + no known agent-error patterns.

        Case (b) was added 2026-05-17 after the MiOS System Dashboard
        chat: hermes emitted clean markdown tables (~3300 chars), polish
        ran on it, the CPU model wrapped the whole thing in ```markdown
        and hit POLISH_MAX_TOKENS mid-table -- producing a truncated
        code-fenced answer. The raw was already correct; polish made it
        worse. Now we trust raw markdown when it looks structured."""
        if not raw:
            return True
        if self._NARRATION_MARKERS.search(raw):
            return False
        if self._KNOWN_AGENT_ERROR_RE.search(raw):
            return False
        # Short + clean -> skip (original case)
        if len(raw) <= int(self.valves.POLISH_SKIP_SHORT_CHARS):
            return True
        # Long but structured markdown -> skip (new case)
        if self._STRUCTURED_MD_RE.search(raw):
            return True
        return False

    async def _polish_via_cpu(
        self,
        user_text: str,
        raw_output: str,
        emitter: Optional[Callable[..., Awaitable[None]]],
        dispatch_ts: Optional[float] = None,
    ) -> str:
        """Output polish/compose: prefers STRUCTURED tool history from
        the Hermes session JSON over the text-blob raw_output (phase-1
        native multi-agent path; see /usr/share/mios/docs/multi-agent-
        architecture.md). Falls back to raw on any failure."""
        if not self.valves.POLISH_ENABLED:
            return raw_output
        if not raw_output or not raw_output.strip():
            return raw_output
        if self._polish_can_skip(raw_output):
            await self._emit(emitter, "✓ clean → skip polish")
            # Even on skip-polish, strip reasoning leaks ("Thought\n\n",
            # <think>...</think>, <details>...</details>) from the
            # raw text. Hermes uses reasoning-mode models that emit
            # these prefixes; the operator should never see them.
            # Operator-flagged 2026-05-18: "Hey there!" returned
            # "Thought\n\nHello! How can I assist you today?" because
            # polish skipped and the leading "Thought" passed through.
            cleaned = self._strip_outer_md_fence(raw_output)
            cleaned = self._strip_reasoning_leaks(cleaned)
            return cleaned or raw_output

        # Try to load the structured tool history from Hermes session
        # JSON (OpenAI-format messages with tool_calls + tool_result).
        # When available, compose reasons over STRUCTURE; when not,
        # falls back to the legacy text-blob path. Operator directive
        # 2026-05-18 to keep this OpenAI-API-compliant + Day-0-bootc.
        tool_history_json: Optional[str] = None
        if dispatch_ts is not None:
            try:
                msgs = self._load_session_tool_history(dispatch_ts)
                if msgs:
                    tool_history_json = self._render_tool_history_for_compose(msgs)
            except Exception:
                tool_history_json = None
        await self._emit(emitter, "🎨 polish")

        # Append the structured tool history at the bottom of the
        # system prompt when available. The model sees the legacy
        # text-blob raw_output AND the structured tool_history; the
        # structured part is authoritative for success/fail reasoning.
        sys_content = self._POLISH_SYSTEM.format(
            user_prompt=user_text[:2000],
            raw_output=raw_output[:12000],
        )
        if tool_history_json:
            sys_content += (
                "\n\n## STRUCTURED TOOL HISTORY (OpenAI-format; authoritative for success/fail)\n"
                "Below is the tool_call + tool_result message history from\n"
                "the Hermes session for this turn. EACH event includes the\n"
                "tool name, arguments, and (when the tool returned JSON\n"
                "with a `success` field per the MiOS verb convention) a\n"
                "boolean `success`. ALSO reflected here: kanban_* tool\n"
                "calls (task state), memory_save/memory_search (durable\n"
                "context), skill_view/skill_manage (agent self-iteration),\n"
                "and any knowledge_search hits (OWUI RAG corpus).\n"
                "\n"
                "PREFER this structured history over the raw text above\n"
                "when reasoning about which steps ran and what they\n"
                "produced. Cite events by tool name + success state in\n"
                "your answer. Steps NOT present in this history did NOT\n"
                "run -- say so explicitly rather than fabricating.\n"
                "\n"
                f"{tool_history_json[:6000]}\n"
            )
        body = {
            "model": self.valves.POLISH_MODEL,
            "messages": [
                {"role": "system", "content": sys_content},
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
                        await self._emit(emitter, f"⚠️ polish HTTP {resp.status} → raw")
                        return raw_output
                    data = await resp.json()
        except asyncio.TimeoutError:
            await self._emit(emitter, "⏱️ polish timeout → raw")
            return raw_output
        except Exception as e:
            await self._emit(emitter, f"⚠️ polish {type(e).__name__} → raw")
            return raw_output

        msg = (data.get("message") or {})
        polished = (msg.get("content") or msg.get("thinking") or "").strip()
        if not polished:
            await self._emit(emitter, "⚠️ polish=∅ → raw")
            return raw_output

        # Sanity check: if polish is suspiciously short vs raw, suspect
        # truncation; pass raw through with a one-line summary header.
        if len(polished) < min(40, len(raw_output) // 10):
            await self._emit(emitter, "⚠️ polish too short → raw")
            return raw_output

        # Strip the outer ```markdown ... ``` wrapper if the model
        # ignored the no-fence rule. The system prompt explicitly
        # forbids this but qwen2.5-coder:7b sometimes does it anyway,
        # and OWUI then renders the WHOLE answer as a code block
        # (operator-flagged 2026-05-17: every polished response was
        # showing as raw markdown source instead of rendered markup).
        polished = self._strip_outer_md_fence(polished)
        # Strip <think>...</think> + leading "Thought" leaks.
        polished = self._strip_reasoning_leaks(polished)

        # ── Phase-2 Critic reflexion loop ──────────────────────────
        # Only runs when we HAVE structured tool history to reason
        # over (the critic's whole value-add is checking the draft
        # against ground truth); skipped on the text-blob fallback
        # path. Bounded by CRITIC_MAX_ITERATIONS.
        if (self.valves.CRITIC_ENABLED and tool_history_json
                and int(self.valves.CRITIC_MAX_ITERATIONS) > 0):
            for attempt in range(int(self.valves.CRITIC_MAX_ITERATIONS)):
                verdict = await self._critic_via_cpu(
                    user_text, polished, tool_history_json, emitter,
                )
                if verdict.get("verdict") == "approve":
                    await self._emit(emitter, "🧑‍⚖️ ✓ critic approve")
                    break
                issues = verdict.get("issues") or []
                if not issues:
                    break
                await self._emit(emitter,
                    f"🧑‍⚖️ ✎ critic: {len(issues)} issue(s) → revise")
                # Re-compose with the critic's issues fed back.
                polished = await self._recompose_with_critic_feedback(
                    user_text, raw_output, tool_history_json, polished,
                    issues, emitter,
                ) or polished
                polished = self._strip_outer_md_fence(polished)
                polished = self._strip_reasoning_leaks(polished)
        return polished

    _CRITIC_SYSTEM = (
        "You are a Critic Agent. The Compose Agent drafted the answer\n"
        "below. Your job: check the draft against the structured tool\n"
        "history (authoritative ground truth). Spot:\n"
        "  1. Claims of success on tools whose tool_result had success=false\n"
        "  2. Claims of completion for steps NOT present in the history\n"
        "  3. Fabricated specifics (paths/ids/numbers not in any result)\n"
        "  4. Wrong tool attribution (saying tool X was used when Y ran)\n"
        "  5. Missing critical info that IS in the history\n"
        "\n"
        "Output JSON ONLY:\n"
        "  {\"verdict\": \"approve\" | \"revise\",\n"
        "   \"issues\": [\"<one-line issue>\", ...]}\n"
        "\n"
        "If draft accurately reflects the history, verdict=\"approve\",\n"
        "issues=[]. Otherwise verdict=\"revise\", issues=[ specific\n"
        "actionable items the Compose Agent should fix ].\n"
        "Be terse. NO prose preamble.\n"
    )

    async def _critic_via_cpu(
        self,
        user_text: str,
        draft: str,
        tool_history_json: str,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> dict:
        """Critic pass over compose draft. Returns the parsed JSON
        verdict; returns {} on any error (fail-open: skip revision,
        ship the draft)."""
        await self._emit(emitter, "🧑‍⚖️ critic")
        user_msg = (
            f"## OPERATOR ASK\n{user_text[:1500]}\n\n"
            f"## STRUCTURED TOOL HISTORY (authoritative)\n"
            f"{tool_history_json[:6000]}\n\n"
            f"## DRAFT ANSWER (from Compose Agent)\n"
            f"{draft[:4000]}\n\n"
            "## VERDICT (JSON only):"
        )
        body = {
            "model": self.valves.CRITIC_MODEL,
            "messages": [
                {"role": "system", "content": self._CRITIC_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            "options": {
                "num_gpu": 0,
                "num_predict": int(self.valves.CRITIC_MAX_TOKENS),
                "temperature": 0.0,
            },
            "format": "json",
            "keep_alive": -1,
            "stream": False,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=int(self.valves.CRITIC_TIMEOUT_S))
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.valves.REFINE_ENDPOINT.rstrip("/") + "/api/chat",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            await self._emit(emitter, "🧑‍⚖️ ⚠ critic err → ship draft")
            return {}
        except Exception:
            return {}
        msg = (data.get("message") or {})
        content = (msg.get("content") or "").strip()
        if not content:
            return {}
        # Strip code fences a chatty model might add.
        content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    async def _recompose_with_critic_feedback(
        self,
        user_text: str,
        raw_output: str,
        tool_history_json: str,
        prev_draft: str,
        issues: list,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> str:
        """Re-run compose with the critic's specific issue list fed
        back in. The compose model sees:
          * Original system prompt + structured history
          * The previous draft
          * The critic's list of issues to fix
        Returns the revised answer; empty string on any failure (the
        caller keeps the prev_draft in that case)."""
        sys_content = self._POLISH_SYSTEM.format(
            user_prompt=user_text[:2000],
            raw_output=raw_output[:12000],
        )
        sys_content += (
            "\n\n## STRUCTURED TOOL HISTORY (authoritative)\n"
            f"{tool_history_json[:6000]}\n"
            "\n## CRITIC FEEDBACK on your previous draft\n"
            "Your previous draft had these issues -- FIX each one in\n"
            "the revised answer. Use the structured history above to\n"
            "ground every claim. Output the revised final answer only;\n"
            "no preamble, no 'here is the revised version'.\n\n"
        )
        for i, issue in enumerate(issues, 1):
            sys_content += f"  {i}. {str(issue)[:300]}\n"
        sys_content += f"\n## PREVIOUS DRAFT\n{prev_draft[:6000]}\n"
        body = {
            "model": self.valves.POLISH_MODEL,
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": "Emit the revised final answer."},
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
                        return ""
                    data = await resp.json()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return ""
        except Exception:
            return ""
        msg = (data.get("message") or {})
        return (msg.get("content") or msg.get("thinking") or "").strip()

    # Match a leading ```markdown / ``` fence. The closing ``` is
    # OPTIONAL because polish sometimes truncates mid-output (token
    # cap hit on a long table) -- in that case there's an open fence
    # with no close, and OWUI renders the WHOLE answer as a code
    # block. We strip the open fence either way; if a close exists
    # at end-of-text we also drop that. Operator-flagged 2026-05-17:
    # MiOS System Dashboard table came back wrapped in ```markdown
    # because polish ran out of tokens before closing the fence.
    _OUTER_FENCE_RE = re.compile(
        r"^\s*```(?:md|markdown|MD|MARKDOWN)?\s*\n(.*?)(?:\n```\s*)?$",
        re.S,
    )
    # Reasoning leakage in polish output (operator-flagged 2026-05-17:
    # "<think>I need to use the Windows tool instead..." rendered as
    # part of the final answer). Strip <think>...</think>, <reasoning>
    # ...</reasoning>, and bare "Thought\n\n<text>" pattern leaks.
    _THINK_TAG_RE = re.compile(
        r"<\s*(?:think|reasoning|thinking|cot)\s*>.*?<\s*/\s*(?:think|reasoning|thinking|cot)\s*>",
        re.S | re.I,
    )
    _LEADING_THOUGHT_RE = re.compile(
        r"^\s*(?:thought|thinking|reasoning)\s*\n+", re.I,
    )
    # Polish sometimes emits an additional <details type="reasoning">
    # block in its output, on top of the agent-thinking <details> the
    # pipe already wrapped. Operator-flagged 2026-05-18: chat showed
    # two stacked <details> blocks. The polished answer must NEVER
    # contain a <details>; that wrapper is the pipe's job, not the
    # polish model's.
    _DETAILS_BLOCK_RE = re.compile(
        r"<\s*details[^>]*>.*?<\s*/\s*details\s*>",
        re.S | re.I,
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

    def _strip_reasoning_leaks(self, text: str) -> str:
        """Remove <think>/<reasoning>/<details type="reasoning"> tags
        the polish model occasionally emits despite the system prompt
        rule against narration. Operator-flagged 2026-05-17 (think)
        + 2026-05-18 (details). The pipe wraps the AGENT thinking in
        its own <details> block above the polished answer; the polish
        model must NEVER emit its own."""
        text = self._DETAILS_BLOCK_RE.sub("", text)
        text = self._THINK_TAG_RE.sub("", text)
        text = self._LEADING_THOUGHT_RE.sub("", text)
        return text.strip()

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
            await self._emit(emitter, "💬 → skip refine")
            return user_text

        model = self.valves.REFINE_MODEL
        # Sanitized emit (no model name); see polish emit comment above.
        await self._emit(emitter, "🧠 refine")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._refine_system_rendered},
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
                            f"⚠️ refine ollama {r.status} → original")
                        return user_text
                    body = await r.json()
            msg = body.get("message") or {}
            refined = (msg.get("content") or "").strip()
            if not refined:
                # qwen3.5-family thinking-mode -- final answer empty,
                # thinking field has the trace. Use it but mark.
                refined = (msg.get("thinking") or msg.get("reasoning") or "").strip()
            if not refined:
                await self._emit(emitter, "⚠️ refine=∅ → original")
                return user_text
            await self._emit(emitter,
                f"✓ refine {len(user_text)}c → {len(refined)}c")
            return refined
        except asyncio.TimeoutError:
            await self._emit(emitter,
                f"⏱️ refine timeout {self.valves.REFINE_TIMEOUT_S}s → original")
            return user_text
        except Exception as e:
            await self._emit(emitter,
                f"⚠️ refine {type(e).__name__} → original")
            return user_text

    async def _raw_passthrough(
        self,
        body: dict,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> AsyncGenerator[str, None]:
        """Stream the request straight through WITHOUT refinement,
        thinking-wrap, or polish. Used for OWUI's internal task-
        generation calls (title/tags/follow-up/autocomplete/etc.) that
        expect raw JSON or short labels back.

        Operator architecture 2026-05-17: "using hermes immediately
        and not using the MiOS-Agent CPU model(s) ... MiOS-Agent is
        the agents driving the operations and retrying the sub-agents
        (MiOS-Hermes, MiOS-OpenCode, etc-etc)". Routes task-gen to
        the CPU model directly (Ollama /v1/chat/completions, which is
        OpenAI-compat), not to Hermes. Hermes is the heavy
        orchestrator -- spinning it up for trivial title/tag
        generation wastes 30-90s of CPU + delegate-spawn overhead per
        call and was the source of the "hermes immediately" behavior
        the operator flagged."""
        body = dict(body)
        # Route to the CPU refine/polish model, not to Hermes.
        body["model"] = self.valves.REFINE_MODEL
        body["stream"] = True
        # Strip any sampling overrides that would slow the small model
        # down on trivial gen tasks.
        body.pop("tools", None)
        body.pop("tool_choice", None)
        # Cap token budget on task-gen so a runaway generation doesn't
        # eat a full polish-sized output for a title.
        body.setdefault("max_tokens", 220)

        # Ollama exposes /v1/chat/completions as an OpenAI-compatible
        # endpoint -- same request + streaming shape as the BACKEND_URL
        # OWUI was hitting before. No client-side transform needed.
        headers = {"Content-Type": "application/json"}
        url = self.valves.REFINE_ENDPOINT.rstrip("/") + "/v1/chat/completions"
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
            await self._emit(emitter, "✅ task-gen", done=True)
        except asyncio.TimeoutError:
            await self._emit(emitter, "⏱️ task-gen timeout", done=True)
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
            # Sanitized: no model name in the emit; task_kind is the
            # OWUI-defined identifier (title_generation, etc.) and
            # stays cross-locale.
            await self._emit(__event_emitter__,
                f"⚙️ task-gen ({task_kind})")
            async for chunk in self._raw_passthrough(body, __event_emitter__):
                yield chunk
            return

        # Status emits use short symbol+term form, no English narrative
        # (operator directive 2026-05-17: GLOBAL SWEEP -- "remove any
        # hardcoded english (other than generic technically accurate
        # terminologies)"). Tool/model names stay since they're
        # cross-locale identifiers; verbs like "receiving" -> emoji.
        await self._emit(__event_emitter__, "📡 prompt")

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

        await self._emit(__event_emitter__, "🧠 → hermes")
        # Mark the dispatch moment so compose (after hermes finishes
        # streaming) can find the matching Hermes session JSON by
        # mtime > _dispatch_ts. Shared mutable scratch location:
        # /var/lib/mios/hermes/sessions/ (operator directive 2026-05-18
        # "shared global scratpad(s) in mutable locations").
        _dispatch_ts = time.time()

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
        # Operator-flagged 2026-05-18: open `<details>` was being
        # yielded EAGERLY before hermes responded -- if hermes was
        # cold-loading a model (30-90s) the operator saw the open tag
        # alone, and if hermes returned empty, the close was missed
        # and OWUI rendered the rest of the message as
        # collapsed-reasoning. Fix: lazy-open. We only emit the open
        # tag the first time a real chunk arrives. _details_opened
        # tracks state so the close path knows whether to emit a
        # matching close.
        _details_opened = False

        def _open_details_chunk() -> str:
            return (
                f"<details type=\"reasoning\" data-mios-agent=\"hermes\">\n"
                f"<summary>{self.valves.AGENT_THINKING_LABEL}</summary>\n\n"
            )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers,
                                        data=json.dumps(body).encode()) as resp:
                    if resp.status != 200:
                        err = (await resp.text())[:300]
                        # Nothing to close yet -- we never opened.
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
                        # Lazy-open: emit the <details> opener only
                        # when the FIRST chunk arrives.
                        if self.valves.POLISH_ENABLED and not _details_opened:
                            yield _open_details_chunk()
                            _details_opened = True
                        yield text_piece

            # Close the thinking block before polish, BUT only if we
            # actually opened it. An empty-output turn (hermes never
            # streamed) never opens, so never closes -- the operator
            # sees the empty marker below without any orphaned tag.
            if _details_opened:
                yield "\n</details>\n\n"

            raw_text = raw_buffer.strip()

            if not any_text or not raw_text:
                yield "_⚠️ ∅_"
                await self._emit(__event_emitter__, "✅", done=True)
                return

            # If polish is OFF, the legacy flow already emitted text
            # via yield above; nothing more to do.
            if not self.valves.POLISH_ENABLED:
                await self._emit(__event_emitter__, "✅", done=True)
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
                dispatch_ts=_dispatch_ts,
            )
            yield polished

            await self._emit(__event_emitter__, "✅", done=True)
        except asyncio.TimeoutError:
            # Close the <details> ONLY if lazy-open actually fired.
            # No tag was emitted on empty-stream / cold-load timeouts
            # so we don't orphan a close either.
            if _details_opened:
                yield "\n</details>\n\n"
            await self._emit(__event_emitter__,
                             f"⏱️ {self.valves.TIMEOUT_S}s",
                             done=True)
            yield f"\n\n_⏱️ {self.valves.TIMEOUT_S}s_"
        except Exception as e:
            if _details_opened:
                yield "\n</details>\n\n"
            await self._emit(__event_emitter__,
                             f"❌ {type(e).__name__}: {e}",
                             done=True)
            yield f"\n\n_❌ {type(e).__name__}: {e}_"
        finally:
            stop_tail.set()
            try:
                await asyncio.wait_for(tail_task, timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                pass

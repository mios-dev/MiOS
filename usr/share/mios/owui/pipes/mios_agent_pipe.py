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
            default="http://host.containers.internal:8641/v1",
            description="OpenAI-compat backend (prefilter @ :8641, which forces delegate_task + forwards to hermes @ :8642). OWUI runs in a podman Quadlet so the host is reached via host.containers.internal.",
        )
        BACKEND_MODEL: str = Field(
            default="MiOS-Agent",
            description="Model name to pass upstream (prefilter rewrites to hermes-agent).",
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
            default="qwen3.5:4b",
            description="Small CPU model used for refinement. Must be small enough to refine in <5s on the host's CPU (qwen3.5:4b ~3.4 GB; qwen3:1.7b ~1.4 GB; qwen3:0.6b-cpu ~522 MB). Loaded once with keep_alive=-1, stays warm forever.",
        )
        REFINE_ENDPOINT: str = Field(
            default="http://host.containers.internal:11434",
            description="Ollama endpoint for the refine call. Hits /api/chat (NOT /v1, which drops options field).",
        )
        REFINE_TIMEOUT_S: int = Field(
            default=20,
            description="Hard cap on the refine call. Should comfortably exceed warm-call latency on the host's CPU. On timeout the pipe falls through to original prompt (NOT 503; pipe is OWUI-facing and 503 would be a bad UX).",
        )
        REFINE_MAX_TOKENS: int = Field(
            default=300,
            description="Cap refine output. Smaller = faster turn. 300 tokens is enough for INTENT + 2-3 step PLAN.",
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

    _CONVERSATIONAL_RE = re.compile(
        r"^\s*(hi|hello|hey|yo|howdy|sup|gm|gn|"
        r"good (morning|afternoon|evening|night)|"
        r"ok|okay|kk|thanks|thx|ty|cool|nice|great|got it|sure|yes|no|yep|nope|"
        r"bye|cya|goodbye|later|peace|"
        r"what'?s up|how are you|how'?s it going)[!?.\s]*$",
        re.IGNORECASE,
    )

    _REFINE_SYSTEM = (
        "/nothink\n"
        "You are MiOS-Agent on a MiOS host. The user typed a short request "
        "in OWUI. Rewrite it as a clearer, more contextualized prompt for "
        "the downstream MiOS-Hermes orchestrator (and its delegated "
        "sub-agents). Add: explicit intent, any plausible MiOS helpers "
        "to consider (mios-launch / mios-everything / mios-apps / "
        "launch_app / everything_search / system_status / discord_send_"
        "message / browser_navigate), and a brief 2-3 step plan. Keep it "
        "TIGHT -- under 200 tokens. Output ONLY the rewritten prompt, "
        "no preamble, no template headers, no commentary."
    )

    def _looks_conversational(self, text: str) -> bool:
        if not text:
            return True
        if len(text.strip()) > 80:
            return False
        return bool(self._CONVERSATIONAL_RE.match(text.strip()))

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

        text_buffer = ""
        any_text = False
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers,
                                        data=json.dumps(body).encode()) as resp:
                    if resp.status != 200:
                        err = (await resp.text())[:300]
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
                        text_buffer += text_piece
                        emit_text, text_buffer = self._process_buffer(text_buffer)
                        if emit_text:
                            yield emit_text

            # Flush any trailing buffered text (no terminating newline)
            if text_buffer:
                # Wrap whole-trailing-line if narration, else pass through
                if self.valves.COLLAPSE_NARRATION and _is_narration_line(text_buffer):
                    yield f"<think>{text_buffer.rstrip()}</think>"
                else:
                    yield text_buffer

            if not any_text:
                yield "_(MiOS-Agent: backend returned no content)_"

            await self._emit(__event_emitter__, "✅ MiOS-Agent: done", done=True)
        except asyncio.TimeoutError:
            await self._emit(__event_emitter__,
                             f"⏱️  timeout after {self.valves.TIMEOUT_S}s",
                             done=True)
            yield f"\n\n_(MiOS-Agent: backend timed out)_"
        except Exception as e:
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

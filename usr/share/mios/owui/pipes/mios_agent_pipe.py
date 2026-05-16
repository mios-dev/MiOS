"""
title: MiOS-Agent
author: MiOS
version: 1.0.0
description: |
  Consolidated MiOS systems agent. Routes operator chat through the
  delegation-prefilter -> hermes-agent pipeline + adds OWUI EventEmitter
  events so the operator sees sub-agent thinking, tool calls, and
  progress in real time. Intercepts the Qwen-style <function=X> markup
  hermes's underlying model occasionally leaks + converts to proper
  OWUI tool-call display events.

  Operator directives 2026-05-16:
    * "OWUI's MiOS-Agent is the 'model' that users speak to"
    * "should be using OWUI's emitter function to emit the active
       agents/sub-agents thoughts/thinking"
    * "OWUI should emit all global agents printing/answers/etc"

  This pipe is the canonical user-facing entry point. Backend is
  configurable via valves; default points at the prefilter (:8641)
  which itself routes to hermes (:8642). Knowledge bases + memory
  + tools attached at the OWUI Model layer flow through this pipe
  automatically (OWUI augments messages with retrieved context
  before invoking pipe()).
"""

from pydantic import BaseModel, Field
import json
import re
import asyncio
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, Union

import aiohttp


# ─── Qwen-style XML function-call markup the model sometimes leaks ────
# hermes uses OpenAI-format tool_calls. The XML markup goes to the chat
# as visible text + the tool NEVER fires. Detect + emit as tool_call
# status event so OWUI shows it as a tool invocation chip instead of
# raw text. We don't actually execute the parsed call here (hermes is
# the executor); we just surface what the model attempted.
QWEN_FUNCTION_RE = re.compile(
    r"<function=([a-zA-Z_-]+)>\s*"
    r"(?:<parameter=([a-zA-Z_-]+)>\s*(.*?)\s*</parameter>\s*)*"
    r"</function>(?:\s*</tool_call>)?",
    re.DOTALL,
)


class Pipe:
    class Valves(BaseModel):
        BACKEND_URL: str = Field(
            default="http://host.containers.internal:8641/v1",
            description="OpenAI-compat backend (default: MiOS delegation prefilter).",
        )
        BACKEND_MODEL: str = Field(
            default="MiOS-Agent",
            description="Model name to pass upstream (prefilter rewrites to hermes-agent).",
        )
        BACKEND_KEY: str = Field(
            default="",
            description="Bearer key for the backend (leave empty to pass through caller's key).",
        )
        DISPLAY_NAME: str = Field(
            default="MiOS-Agent",
            description="Name shown in OWUI's model dropdown.",
        )
        EMIT_STATUS: bool = Field(
            default=True,
            description="Emit status events ('thinking...', 'calling tool X...').",
        )
        EMIT_XML_MARKUP_AS_TOOL_CALLS: bool = Field(
            default=True,
            description="Convert leaked Qwen <function=X> markup to tool_call emitter events.",
        )
        TIMEOUT_S: int = Field(
            default=300,
            description="Total HTTP timeout when calling the backend.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.name = "MiOS-Agent"

    def pipes(self):
        """OWUI calls this to enumerate the model entries this pipe provides."""
        return [{"id": "mios-agent", "name": self.valves.DISPLAY_NAME}]

    async def _emit(
        self,
        emitter: Optional[Callable[..., Awaitable[None]]],
        description: str,
        done: bool = False,
    ) -> None:
        """Send a status event to OWUI's UI (visible as a progress chip)."""
        if not (self.valves.EMIT_STATUS and emitter):
            return
        try:
            await emitter({
                "type": "status",
                "data": {"description": description, "done": done},
            })
        except Exception:
            pass

    async def _emit_tool_call(
        self,
        emitter: Optional[Callable[..., Awaitable[None]]],
        name: str,
        args: dict,
    ) -> None:
        """Emit a 'tool was called' event for visibility (OWUI shows a chip)."""
        if not (self.valves.EMIT_STATUS and emitter):
            return
        args_preview = json.dumps(args)[:120]
        await self._emit(emitter, f"🛠️  tool: {name}({args_preview})")

    def _strip_and_emit_xml(
        self,
        text: str,
        emitter: Optional[Callable[..., Awaitable[None]]],
    ) -> tuple[str, list[asyncio.Task]]:
        """If `text` contains Qwen-style <function=X> markup, replace with
        a brief placeholder + schedule emit events for each detected call.
        Returns (cleaned_text, list_of_pending_emit_tasks)."""
        if not (self.valves.EMIT_XML_MARKUP_AS_TOOL_CALLS and emitter):
            return text, []
        if "<function=" not in text:
            return text, []
        tasks: list[asyncio.Task] = []
        def _replace(m: re.Match) -> str:
            name = m.group(1)
            # Re-parse parameters within the matched block
            params = {}
            for pm in re.finditer(r"<parameter=([a-zA-Z_-]+)>\s*(.*?)\s*</parameter>",
                                  m.group(0), re.DOTALL):
                params[pm.group(1)] = pm.group(2)
            tasks.append(asyncio.create_task(self._emit_tool_call(emitter, name, params)))
            return f"_[tool call: {name}({', '.join(params)})]_"
        cleaned = QWEN_FUNCTION_RE.sub(_replace, text)
        return cleaned, tasks

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
        """Main streaming entry point. Forwards to backend + emits events.

        V1.1 (2026-05-16): simplified to plain text passthrough after a
        TransferEncodingError was observed in OWUI on the V1 streaming
        path. The XML interception + cross-chunk accumulator were the
        likely source of empty yields confusing OWUIs response framing.
        This version just yields each non-empty content delta as-is and
        emits status events at the start + on completion.
        """
        await self._emit(__event_emitter__, "📡 MiOS-Agent: receiving prompt...")

        # Rewrite model name to backend's expected value
        body = dict(body)
        body["model"] = self.valves.BACKEND_MODEL
        body["stream"] = True

        headers = {"Content-Type": "application/json"}
        if self.valves.BACKEND_KEY:
            headers["Authorization"] = f"Bearer {self.valves.BACKEND_KEY}"

        await self._emit(__event_emitter__, "🧠 MiOS-Agent: dispatching to hermes (xhigh reasoning)...")

        timeout = aiohttp.ClientTimeout(total=self.valves.TIMEOUT_S)
        url = self.valves.BACKEND_URL.rstrip("/") + "/chat/completions"

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
                        if text_piece:
                            any_text = True
                            yield text_piece

            if not any_text:
                # Backend returned no text -- surface that explicitly
                # instead of leaving the chat empty.
                yield "_(MiOS-Agent: backend returned no content)_"

            await self._emit(__event_emitter__, "✅ MiOS-Agent: done", done=True)
        except asyncio.TimeoutError:
            await self._emit(__event_emitter__,
                             f"⏱️  timeout after {self.valves.TIMEOUT_S}s",
                             done=True)
            yield f"\n\n_(MiOS-Agent: backend timed out after {self.valves.TIMEOUT_S}s)_"
        except Exception as e:
            await self._emit(__event_emitter__,
                             f"❌ pipe error: {type(e).__name__}: {e}",
                             done=True)
            yield f"\n\n_(MiOS-Agent: pipe error: {type(e).__name__}: {e})_"

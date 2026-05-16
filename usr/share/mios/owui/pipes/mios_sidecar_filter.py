"""
title: MiOS Agents Sidecar
author: MiOS
version: 1.0.0
description: |
  Surfaces sibling-agent activity in the OWUI chat stream via
  __event_emitter__. Without this Filter, the operator sees ONLY
  MiOS-Hermes's text output -- but every other global agent on
  the host (MiOS-Sys-Agent, mios-agent-nudger, mios-log-watcher,
  mios-cron-director, the qwen3:0.6b-cpu observer micro-LLMs) is
  doing work invisibly into /var/lib/mios/*/latest.json and
  journal entries.

  Operator directive 2026-05-16: "OWUI doesn't emit anything from
  ANY GLOBAL AGENTS as it should" -- this Filter is the bridge.

  INLET (before the model sees the prompt): emit a status event
  for any sibling-agent activity that just happened (e.g.,
  "MiOS-Sys-Agent refined prompt" if the delegation-prefilter
  rewrote the input within the last few seconds).

  OUTLET (after the model responds): emit status events for
  sibling activity that happened DURING the turn (nudger refusal
  detections on this response, new log-watcher classifications,
  cron-director firings). Operator now sees the full federation,
  not just the front-of-house chatbot.

  State tracking: each sibling-agent state file's mtime is cached
  per-chat (in /var/lib/mios/owui-sidecar/) so we only emit
  EVENTS NEW SINCE LAST EMIT. Stale events stay quiet.

  Toggle: per-chat Valves let the operator silence individual
  sources (e.g., nudger-only, no log-watcher noise).
"""

import json
import os
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field


# ─── Where each sibling agent writes its state ────────────────────────
# Keep IN SYNC with the source scripts (mios-agent-nudger,
# mios-log-watcher, mios-cron-director, mios-delegation-prefilter).
# Each entry: (label, path, formatter_fn-name-on-self)
SIBLING_AGENTS = [
    ("nudger",          "/var/lib/mios/agent-nudger/latest.json",       "_format_nudger"),
    ("log-watcher",     "/var/lib/mios/log-watcher/latest.json",        "_format_log_watcher"),
    ("cron-director",   "/var/lib/mios/cron-director/state.json",       "_format_cron"),
    ("sys-agent",       "/var/lib/mios/delegation-prefilter/latest.json","_format_sys_agent"),
]

CACHE_DIR = Path("/var/lib/mios/owui-sidecar")


class Filter:
    class Valves(BaseModel):
        ENABLED: bool = Field(default=True, description="Master on/off.")
        EMIT_NUDGER: bool = Field(default=True, description="Surface refusal-pattern alerts.")
        EMIT_LOG_WATCHER: bool = Field(default=True, description="Surface log-watcher classifications.")
        EMIT_CRON_DIRECTOR: bool = Field(default=True, description="Surface cron firings.")
        EMIT_SYS_AGENT: bool = Field(default=True, description="Surface prompt-refinement events.")
        STALENESS_SECONDS: int = Field(
            default=300,
            description="Don't emit state-file events older than this many seconds.",
        )

    def __init__(self):
        self.valves = self.Valves()
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # ─── Per-chat last-seen-mtime cache ──────────────────────────────
    def _cache_path(self, chat_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(chat_id)) or "default"
        return CACHE_DIR / f"{safe}.json"

    def _load_cache(self, chat_id: str) -> dict:
        p = self._cache_path(chat_id)
        if not p.is_file():
            return {}
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}

    def _save_cache(self, chat_id: str, cache: dict) -> None:
        try:
            self._cache_path(chat_id).write_text(json.dumps(cache))
        except Exception:
            pass

    # ─── Per-agent formatters: each returns a short status string ────
    def _format_nudger(self, payload: dict) -> Optional[str]:
        # Expected shape: {"trigger": "<phrase>", "model": "...", "ts": ...}
        trigger = payload.get("trigger") or payload.get("phrase") or payload.get("pattern")
        if not trigger:
            return None
        return f"⚠️ mios-agent-nudger: refusal-pattern hit -- '{trigger[:80]}'"

    def _format_log_watcher(self, payload: dict) -> Optional[str]:
        # Expected: {"tag": "...", "count": N, "ts": ...} or {"events": [...]}
        tag = payload.get("tag") or payload.get("classification")
        count = payload.get("count") or len(payload.get("events", []) or [])
        if not tag and not count:
            return None
        return f"📊 mios-log-watcher: {tag or 'classified'} ({count or '?'} events)"

    def _format_cron(self, payload: dict) -> Optional[str]:
        # Expected: {"last_fire": {"rule": "...", "ts": ...}}
        last = payload.get("last_fire") or payload.get("last")
        if isinstance(last, dict):
            rule = last.get("rule") or last.get("name") or "rule"
            return f"⏱️ mios-cron-director: fired '{rule}'"
        return None

    def _format_sys_agent(self, payload: dict) -> Optional[str]:
        # Expected: {"original": "...", "refined": "...", "ts": ...}
        if "refined" in payload or "intent" in payload:
            intent = (payload.get("intent") or "")[:80]
            return f"🧠 mios-sys-agent: refined prompt" + (f" ({intent}...)" if intent else "")
        return None

    # ─── Walk every sibling file, emit only NEW activity ─────────────
    def _gather_new_events(self, chat_id: str) -> list[tuple[str, str]]:
        cache = self._load_cache(chat_id)
        now = time.time()
        events: list[tuple[str, str]] = []
        new_cache = dict(cache)

        toggle_for = {
            "nudger": self.valves.EMIT_NUDGER,
            "log-watcher": self.valves.EMIT_LOG_WATCHER,
            "cron-director": self.valves.EMIT_CRON_DIRECTOR,
            "sys-agent": self.valves.EMIT_SYS_AGENT,
        }

        for label, path, fmt_name in SIBLING_AGENTS:
            if not toggle_for.get(label, True):
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            mtime = st.st_mtime
            # Skip if older than staleness window
            if (now - mtime) > self.valves.STALENESS_SECONDS:
                continue
            # Skip if we already emitted this mtime for this chat
            if cache.get(label) and abs(cache[label] - mtime) < 0.001:
                continue
            try:
                payload = json.loads(Path(path).read_text())
            except Exception:
                continue
            fmt = getattr(self, fmt_name, None)
            if not callable(fmt):
                continue
            msg = fmt(payload)
            if msg:
                events.append((label, msg))
                new_cache[label] = mtime

        if new_cache != cache:
            self._save_cache(chat_id, new_cache)
        return events

    async def _emit(self, emitter: Optional[Callable[..., Awaitable]], description: str, done: bool = True):
        if not emitter:
            return
        try:
            await emitter({"type": "status", "data": {"description": description, "done": done}})
        except Exception:
            pass

    # ─── OWUI Filter contract ────────────────────────────────────────
    async def inlet(
        self,
        body: dict,
        __event_emitter__: Optional[Callable[..., Awaitable]] = None,
        __metadata__: Optional[dict] = None,
        __user__: Optional[dict] = None,
    ) -> dict:
        if not self.valves.ENABLED:
            return body
        chat_id = (__metadata__ or {}).get("chat_id") or "default"
        for label, msg in self._gather_new_events(chat_id):
            await self._emit(__event_emitter__, msg, done=True)
        return body

    async def outlet(
        self,
        body: dict,
        __event_emitter__: Optional[Callable[..., Awaitable]] = None,
        __metadata__: Optional[dict] = None,
        __user__: Optional[dict] = None,
    ) -> dict:
        if not self.valves.ENABLED:
            return body
        chat_id = (__metadata__ or {}).get("chat_id") or "default"
        # Brief settle delay so nudger/log-watcher have a chance to react
        # to THIS turn's response before we read their state.
        time.sleep(0.4)
        for label, msg in self._gather_new_events(chat_id):
            await self._emit(__event_emitter__, msg, done=True)
        return body

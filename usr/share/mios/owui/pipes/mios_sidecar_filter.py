# AI-hint: Injects sibling-agent activities (Sys-Agent, nudger, log-watcher, cron-director) into the OWUI chat stream by polling state files and emitting status events to provide the operator visibility into the full MiOS federation.
# AI-related: mios-agent-nudger, mios-log-watcher, mios-cron-director, mios-hermes-tail, mios-delegation-prefilter, mios-daemon, mios-sys-agent
# AI-functions: __init__, _cache_path, _load_cache, _save_cache, _format_hermes_tail, _format_nudger, _format_log_watcher, _format_cron, _format_daemon_classify, _format_daemon_refusal, _format_daemon_cron, _format_sys_agent
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
# Two writers feed this filter:
#   * mios-hermes-tail        -> hermes-tail/latest.json (in-flight tools)
#   * mios-delegation-prefilter -> delegation-prefilter/latest.json (refiner)
#   * mios-daemon (consolidated micro-LLM) -> daemon/state.json with
#        three sub-objects (classify/refusal/cron) that mirror the old
#        per-service files. ONE poll -> three categories of events.
#
# The unified mios-daemon state file replaces the three predecessor
# files (nudger / log-watcher / cron-director) -- the daemon writes
# them under a single roof. Old per-service paths are kept in the
# fallback table below ONLY for compatibility with hosts that haven't
# rebooted into the consolidated daemon yet; they'll be removed in a
# future commit once the migration window closes.
SIBLING_AGENTS = [
    ("hermes-tail",     "/var/lib/mios/hermes-tail/latest.json",         "_format_hermes_tail"),
    ("sys-agent",       "/var/lib/mios/delegation-prefilter/latest.json","_format_sys_agent"),
    # NEW unified daemon
    ("daemon-classify", "/var/lib/mios/daemon/state.json",               "_format_daemon_classify"),
    ("daemon-refusal",  "/var/lib/mios/daemon/state.json",               "_format_daemon_refusal"),
    ("daemon-cron",     "/var/lib/mios/daemon/state.json",               "_format_daemon_cron"),
    # Legacy fallbacks (pre-mios-daemon hosts -- deprecated)
    ("nudger",          "/var/lib/mios/agent-nudger/latest.json",        "_format_nudger"),
    ("log-watcher",     "/var/lib/mios/log-watcher/latest.json",         "_format_log_watcher"),
    ("cron-director",   "/var/lib/mios/cron-director/state.json",        "_format_cron"),
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
    def _format_hermes_tail(self, payload: dict) -> Optional[str]:
        # Expected shape: {"ts", "events": [...], "active_session_count",
        #                  "inflight_subagents"}. Surfaces the MOST RECENT
        # event with priority weighting -- chronic failure modes
        # (invalid_tool, max_retries) are highlighted; routine tool
        # calls only emit if no failure is in the recent window.
        events = payload.get("events", [])
        if not events:
            return None
        # Priority sort: failures first, then synthesis/spawn, then routine.
        priority = {
            "max_retries":    0,
            "invalid_tool":   1,
            "retry":          2,
            "delegate_spawn": 3,
            "synthesis":      4,
            "subagent_done":  5,
            "tool_call":      6,
        }
        events_sorted = sorted(events, key=lambda e: priority.get(e.get("kind"), 99))
        top = events_sorted[0]
        kind = top.get("kind", "")
        detail = top.get("detail", "")
        icons = {
            "max_retries":    "❌",
            "invalid_tool":   "⚠️",
            "retry":          "↻",
            "delegate_spawn": "🚀",
            "synthesis":      "🔀",
            "subagent_done":  "✓",
            "tool_call":      "⚙️",
        }
        icon = icons.get(kind, "·")
        suffix = ""
        inflight = payload.get("inflight_subagents", 0)
        if inflight > 0 and kind in ("delegate_spawn", "tool_call"):
            suffix = f" ({inflight} inflight)"
        return f"{icon} hermes: {detail}{suffix}"

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

    # ─── Formatters for the unified mios-daemon state file ─────────
    # Sub-objects under daemon/state.json: {classify, refusal, cron}.
    # Each formatter reads its OWN sub-key from the same blob; the
    # three SIBLING_AGENTS entries for "daemon-*" all point at the
    # same file but render different categories.

    def _format_daemon_classify(self, payload: dict) -> Optional[str]:
        c = payload.get("classify") or {}
        if not c:
            return None
        summary = c.get("summary") or ""
        if summary.startswith("(unparseable") or summary.startswith("(JSON err"):
            return None  # don't emit noise
        sev = c.get("severity", "?")
        n = c.get("event_count", "?")
        return f"📊 mios-daemon classify: {summary[:140]} ({n} events, sev={sev})"

    def _format_daemon_refusal(self, payload: dict) -> Optional[str]:
        r = payload.get("refusal") or {}
        trig = r.get("trigger") or r.get("phrase")
        if not trig:
            return None
        return f"⚠️ mios-daemon refusal: '{trig[:80]}'"

    def _format_daemon_cron(self, payload: dict) -> Optional[str]:
        c = payload.get("cron") or {}
        last = c.get("last_fire")
        if not isinstance(last, dict):
            return None
        rule = last.get("rule") or "rule"
        return f"⏱️ mios-daemon cron: fired '{rule}'"

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

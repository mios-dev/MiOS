# AI-hint: WS-LIFECYCLE-VER prompt-version registry (the PURE half). The ~12 agent-pipe hop prompts (router/refine/synthesis/polish/swarm/native-loop system templates) were UNVERSIONED -- no content-hash, no version, no rollback -- so there is no substrate for the self-improve ACT half (WS-11) to safely roll an auto-edited prompt forward/back. PromptRegistry.register(name, content) stamps a stable sha256 content-hash + a version that increments ONLY when the content changes; keeps a bounded history so rollback() restores the prior content as a new version; snapshot() (content-free) feeds /v1/prompts observability + drift detection. Pure stdlib + deterministic so it unit-tests in isolation; server.py registers the live hop-prompt constants at import + exposes the surface. Sibling of mios_registry/mios_capreg.
# AI-related: ./server.py, ./mios_registry.py, ./mios_selfimprove.py, /usr/share/mios/mios.toml, ./test_mios_promptver.py
# AI-functions: content_hash, register, current, history, rollback, snapshot, class PromptRegistry
"""mios_promptver -- versioned registry for the agent-pipe hop prompts (WS-LIFECYCLE-VER).

The completeness critic flagged it: MiOS versions skill/recipe PACKAGES (WS-A17)
but the LIVE refine/synthesis/polish/swarm/council/native-loop system prompts
carry no version stamp, no A/B, no rollback. That is the missing PREREQUISITE for
the self-improve ACT half (WS-11): you cannot safely auto-edit a prompt without a
way to identify the live version + roll it back.

This module is the PURE substrate:
  * content_hash() -- stable sha256[:12] of a prompt's text.
  * PromptRegistry.register(name, content) -- stamp a version that bumps ONLY on
    a content change (idempotent for an unchanged prompt); bounded history.
  * rollback(name) -- restore the previous content as a NEW (forward) version.
  * snapshot() -- content-free {name -> version/hash/len/history} for /v1/prompts.

server.py registers the live prompt constants at import + exposes the surface;
this owns the deterministic versioning logic.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional


def content_hash(text: object) -> str:
    """Stable short content fingerprint (sha256, first 12 hex). Deterministic."""
    return hashlib.sha256(str(text if text is not None else "").encode(
        "utf-8", "replace")).hexdigest()[:12]


class PromptRegistry:
    """Versioned, rollback-capable registry of named prompts. Single event loop;
    no lock (registration is at import + the rare self-improve edit)."""

    def __init__(self, history: int = 8) -> None:
        self._cur: "Dict[str, dict]" = {}        # name -> {version,hash,len,content}
        self._hist: "Dict[str, List[dict]]" = {}  # name -> [prior recs, oldest..newest]
        self._h = max(1, int(history))

    def register(self, name: str, content: str) -> dict:
        """Stamp `content` for `name`. Returns the current record. The version
        bumps ONLY when the content differs from the last registered (so calling
        it every import with an unchanged prompt keeps version stable -- the hash
        is the drift signal). The replaced record is pushed to bounded history."""
        name = str(name)
        h = content_hash(content)
        cur = self._cur.get(name)
        if cur and cur["hash"] == h:
            return cur                            # unchanged -> stable version
        version = (cur["version"] + 1) if cur else 1
        rec = {"name": name, "version": version, "hash": h,
               "len": len(str(content if content is not None else "")),
               "content": str(content if content is not None else "")}
        if cur:
            self._hist.setdefault(name, []).append(
                {k: cur[k] for k in ("version", "hash", "content")})
            self._hist[name] = self._hist[name][-self._h:]
        self._cur[name] = rec
        return rec

    def current(self, name: str) -> "Optional[dict]":
        return self._cur.get(str(name))

    def history(self, name: str) -> "List[dict]":
        return list(self._hist.get(str(name), []))

    def rollback(self, name: str) -> "Optional[dict]":
        """Restore the PREVIOUS version's content as the new current (a forward
        version bump whose content equals the prior). None if no history. This is
        the safety net for an auto-edited prompt that regressed."""
        hist = self._hist.get(str(name))
        if not hist:
            return None
        prev = hist[-1]
        return self.register(name, prev["content"])

    def snapshot(self) -> dict:
        """Content-FREE registry view (version/hash/len + history depth per name)
        for /v1/prompts + drift detection. Never leaks the prompt text."""
        return {n: {"version": r["version"], "hash": r["hash"], "len": r["len"],
                    "history": len(self._hist.get(n, []))}
                for n, r in sorted(self._cur.items())}

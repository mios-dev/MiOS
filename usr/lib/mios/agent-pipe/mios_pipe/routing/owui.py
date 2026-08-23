# AI-hint: Adapter for Open WebUI requests that identifies and strips OWUI-specific RAG/task templates to isolate the raw user query from downstream processing in the agent-pipe.
# AI-functions: strip_owui_scaffold
from __future__ import annotations

import re

__all__ = ["OWUI_TEMPLATE_MARKERS", "strip_owui_scaffold"]

OWUI_TEMPLATE_MARKERS = (
    "respond to the user query using the provided context",
    "generate a concise",          # OWUI title-generation task
    "broad tags categorizing",     # OWUI tags-generation task
    "analyze the chat history",     # OWUI query/search-generation task
    "you are an autocompletion",    # OWUI autocomplete task
)


def strip_owui_scaffold(text: str) -> str:
    if not text:
        return text
    low = text.lower()
    _is_owui = (any(m in low for m in OWUI_TEMPLATE_MARKERS)
                or ("### task:" in low and "</context>" in low)
                or "<user_query>" in low)
    if not _is_owui:
        return text
    if "<" in text:
        for tag in ("user_query", "query", "question", "prompt"):
            m = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text,
                          flags=re.IGNORECASE | re.DOTALL)
            if m and m.group(1).strip():
                return m.group(1).strip()
    m = re.search(r"</context>\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        cand = m.group(1).strip()
        if cand and "### task:" not in cand.lower() \
                and "<context>" not in cand.lower():
            return cand
    head = re.split(r"###\s*task\s*:", text, maxsplit=1,
                    flags=re.IGNORECASE)[0].strip()
    if head and "<context>" not in head.lower() and "</context>" not in head.lower():
        return head
    return text

# AI-hint: Adapter for Open WebUI requests that identifies and strips OWUI-specific RAG/task templates to isolate the raw user query from downstream processing in the agent-pipe.
# AI-functions: strip_owui_scaffold
"""Open WebUI request adapter.

Extracted from server.py (monolith split). Pure stdlib (re) -- NO
coupling to the agent-pipe globals. Isolates the OWUI-specific quirk of wrapping
the user message in its RAG/task template so the rest of the pipe only ever sees
the operator's genuine question. The marker strings here are OWUI's OWN fixed
template text (an external-format adapter, like a protocol constant) -- not
operator-tunable config.
"""
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
    """Return the operator's genuine question, unwrapping any OWUI task template.

 OWUI's native web-search/RAG (ENABLE_WEB_SEARCH, confirmed live)
    wraps the message in its DEFAULT_RAG_TEMPLATE -- "### Task:\\nRespond to the
    user query using the provided context ... <context>{sources}</context>" -- and
    the CURRENT default has NO <user_query> placeholder: the real question is just
    APPENDED after </context>. So the old strip (which required a <user_query> tag)
    silently passed the WHOLE blob through, and that blob became refine's text +
    every swarm facet title + the web-search query + each node's prompt ("respond
    using the provided context" -> the node RAG-answers / refuses tools) -- the
    operator's "PRIOR PROMPTS SATURATE PIPELINE" + the "### Task:" facet searches +
    the punts. Recover the genuine question. (Native-OpenAI pattern: retrieved
    context belongs in a system message, never concatenated into the user turn;
    MiOS does its OWN retrieval, so OWUI's injected context is dropped here.)

    Safe by construction: only unwraps a RECOGNISED OWUI scaffold (its marker
    sentence, or '### task:' + a '</context>' block, or an explicit <user_query>);
    a normal message that merely says 'task' or contains '<' is returned as-is."""
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

<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Open WebUI request adapter. Extracted from server.py...

Open WebUI request adapter.

Extracted from server.py (monolith split). Pure stdlib (re) -- NO
coupling to the agent-pipe globals. Isolates the OWUI-specific quirk of wrapping
the user message in its RAG/task template so the rest of the pipe only ever sees
the operator's genuine question. The marker strings here are OWUI's OWN fixed
template text (an external-format adapter, like a protocol constant) -- not
operator-tunable config.

<!-- mios-src:41917a903e89 from usr/lib/mios/agent-pipe/mios_pipe/routing/owui.py:3-11 -->

### Return the operator's genuine question, unwrapping any OWUI...

Return the operator's genuine question, unwrapping any OWUI task template.

 OWUI's native web-search/RAG (ENABLE_WEB_SEARCH, confirmed live)
    wraps the message in its DEFAULT_RAG_TEMPLATE -- "### Task:\nRespond to the
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
    a normal message that merely says 'task' or contains '<' is returned as-is.

<!-- mios-src:dad236898017 from usr/lib/mios/agent-pipe/mios_pipe/routing/owui.py:28-45 -->

<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Anti-fabrication POLISH/VERITY cluster (final-answer...

Anti-fabrication POLISH/VERITY cluster (final-answer fact-check + figure guard).

Extracted verbatim from ``server.py``. Holds the final-pass VERITY fact-check
(``_verity_factcheck``), the deterministic ungrounded-figure output guard
(``_strip_ungrounded_figures``) and the sub-agent answer re-shaper
(``polish_response``). ``server.py`` re-imports every name under its original
alias so the module's public surface is byte-identical.

The model-call constants (REFINE_*/POLISH_*) and the server-side DB/format/store
helpers are injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``); ``_loads_lenient`` and ``_env_grounding`` come
from sibling modules directly.

<!-- mios-src:e58b1580e92d from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py:3-15 -->

### Generative judge (NO keywords -- operator "NOTHING...

Generative judge (NO keywords -- operator "NOTHING HARDCODED"): is `answer`
    PRIMARILY asking the USER for information it NEEDS to proceed (a clarification /
    missing detail / a choice between options), vs a complete answer or an incidental/
    rhetorical question? If yes, return the SINGLE clearest question to put to the user;
    else ''. The caller gates on a '?' present (cheap structural pre-filter) so this runs
    rarely. Degrade -> '' (no prompt).

<!-- mios-src:2687d0c8001e from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py:145-150 -->

### Drop sentences whose PRICE ($/C$/US$ + digits) or PERCENT...

Drop sentences whose PRICE ($/C$/US$ + digits) or PERCENT (N%) figures are
    absent from the source material polish was given.

 The recurring 4b-polish failure ('FAILURE'): the final
    pass APPENDS invented specifics -- 'deals as low as $184 ... Skyscanner [3]'
    and 'morning departures ~2% cheaper [1]' -- with SCRAMBLED citations, even
    though _POLISH_SYSTEM forbids it. The prompt rule alone doesn't hold on the
    small model, and verity only checks the INPUT draft, never polish's OUTPUT.
    This is the deterministic output-side guard.

    The `haystack` is the FULL material polish saw -- the raw research AND the
    agents' own findings (+ web sources). So a figure is 'grounded' if ANY
    agent or source produced it; only figures polish INVENTED get stripped.
    This is why a general-knowledge numeric answer (agent says '~120 million
    rods') is safe: the number is in the agents' findings = in the haystack.

    Conservative by design: only $-prices and N%-percentages are policed (NOT
    durations / counts / dates / years); prices match by distinctive >=3-digit
    number presence; percentages must have a matching '<n>%' in the source;
    drops at the SENTENCE level within a line (markdown structure preserved);
    and a fail-safe leaves the answer untouched if it would strip more than half
    the figure-bearing sentences (a sign the grounding capture, not the model,
    is at fault).

<!-- mios-src:ff354421da5a from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py:267-289 -->

### Polish a sub-agent's raw response into the final...

Polish a sub-agent's raw response into the final user-facing
    answer. Returns the polished string or None on error (caller
    keeps the raw answer).

    When session_id is supplied, the polish prompt receives the
    recent tool_call history as ground truth. The CRITICAL rule in
    _POLISH_SYSTEM tells the model to REWRITE the response when it
 contradicts the tool history (Operator-flagged
    'open nautilus' -> assistant claimed 'The move command failed
    because the destination directory wasn't writable' -- a
    completely fabricated unrelated error).

    `original_user_text` is the operator's ACTUAL last message and is
    the authoritative LANGUAGE anchor. refined_text is a rewrite the
    (all-English) refine prompt can translate to English -- keying
    polish's reply language off it made a Polish question come back in
 English / mixed. Polish answers in the
    language of the original message; refined_text feeds CONTENT only.

<!-- mios-src:de560e3accca from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py:350-367 -->

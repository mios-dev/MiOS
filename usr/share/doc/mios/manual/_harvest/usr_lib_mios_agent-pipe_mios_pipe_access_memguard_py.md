<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_memguard -- write-time memory-poisoning validation...

mios_memguard -- write-time memory-poisoning validation (WS-MEM-VALIDATE, OWASP ASI08).

A durable-memory store (the knowledge Q/A append) is an injection vector: text
persisted today is RECALLED later and folded into a future turn's context, where
an embedded imperative ("ignore previous instructions...") or a code/exfil
payload can steer the model. MiOS already verdict-gates storage (an UNSATISFIED
turn is not stored), but a SATISFIED answer can still carry poisoned content.

This module is the detector + policy:
  * scan_fact()        -- PURE structural scan -> {flags, severity, has_*}: only
                          language-neutral SHAPES (inert URL / code fence -> low;
                          a control-token delimiter -> a HIGH escalation signal).
  * _judge_severity()  -- MODEL-DRIVEN injection judge: the micro-model classifies
                          whether the write is a prompt-injection / poisoning
                          attempt + its severity. No keyword/English phrase list --
                          intent is judged, so paraphrase / non-English is caught.
  * validate_for_store(mode) -- off | log | strip | reject.

The severity verdict is the MODEL's; the structural scan is a fast-path that can
only ESCALATE (an obvious control-token), never the sole gate. The judge path is
flag-gated ([pgvector].memguard_judge_mode). When the micro lane is unavailable
the verdict DEGRADES to the structural scan (fail-safe -- an obvious control-token
still escalates while benign content still stores; never the deleted keyword gate).

FAIL-OPEN: a scanner/judge error never blocks a store (the memory guard must not
become a new way to drop the user's own answer). server.py owns the wiring + the
SSOT policy mode; this is the deterministic, unit-testable policy.

<!-- mios-src:70884b1cc1a3 from usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py:3-30 -->

### PURE structural scan of a candidate durable-memory fact....

PURE structural scan of a candidate durable-memory fact. Returns
    {flags: [str], severity: none|low|high, has_control_token, has_url,
    has_code_fence}. Deterministic + language-neutral: it flags only SHAPES, never
    English/keyword content. A control-token delimiter -> HIGH (an unambiguous
    injection shape that ESCALATES the model verdict); an inert URL / code fence ->
    LOW; else NONE. The injection/poisoning SEVERITY proper is the MODEL judge's
    (_judge_severity); this scan is the escalation fast-path + the degrade-open
    fallback when the judge is unavailable.

<!-- mios-src:cab8bae7503a from usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py:65-72 -->

### MODEL-DRIVEN prompt-injection / memory-poisoning judge...

MODEL-DRIVEN prompt-injection / memory-poisoning judge (OWASP ASI08): the
    always-warm micro-model decides whether THIS candidate durable-memory write is
    an injection / poisoning attempt and at what SEVERITY. Replaces the deleted
    English-regex phrase gate -- a paraphrased or non-English injection is caught
    because the MODEL classifies INTENT, not a keyword list. Returns "high" (an
    injection/identity-override/poisoning attempt or a dangerous code/exfil payload),
    "low" (benign content, possibly with an inert URL / code sample), "none" (plain
    benign fact), or ``None`` to signal the judge is UNAVAILABLE (lane down / non-200
    / unparseable) -> the caller DEGRADES to the structural verdict (fail-safe, never
    the deleted keyword gate). Degrade-open on any error: never block a store.

<!-- mios-src:5e52985f75ad from usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py:106-115 -->

### Apply the WS-MEM-VALIDATE policy to a candidate fact....

Apply the WS-MEM-VALIDATE policy to a candidate fact. Returns
    {ok, store_text, flags, severity}:
      off    -> always ok, text unchanged (no-op; zero behaviour change).
      log    -> always ok, text unchanged, flags/severity reported (the caller
                emits an audit event when flagged) -- observe-only.
      strip  -> always ok, store_text is the NEUTRALIZED text when flagged.
      reject -> ok=False ONLY on HIGH severity (drop the poisoned fact); LOW/none
                store unchanged.

    SEVERITY is MODEL-DRIVEN: the micro-model injection judge (_judge_severity)
    classifies intent (flag-gated by ``judge_mode`` / [pgvector].memguard_judge_mode,
    default "model"); the structural scan can only ESCALATE it (an obvious
    control-token) and is the DEGRADE-OPEN fallback when the judge is unavailable
    (fail-safe -- an obvious injection still escalates, benign content still stores;
    NEVER a keyword gate, never a silent drop). FAIL-OPEN: any scanner/judge error
    -> ok=True, text unchanged (never lose a store).

<!-- mios-src:c43a4af008b0 from usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py:167-182 -->

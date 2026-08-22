<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-MEM-VALIDATE write-time memory-poisoning guard (OWASP ASI08). Judges a candidate durable-memory fact (a knowledge Q/A about to be persisted) for poisoning -- a prompt-injection / "ignore previous instructions" imperative, a role/identity-override, a dangerous code/exfil payload -- and assigns SEVERITY (high/low/none). Severity is MODEL-DRIVEN: an async micro-model injection judge (_judge_severity, OWASP-ASI08 framed) classifies INTENT, so a paraphrased or non-English injection is caught where a fixed keyword list would miss it -- there is NO English-regex phrase gate. A PURE structural scan (scan_fact) flags only language-neutral SHAPES (an inert URL / code fence -> low; a tokenizer/chat-template control-token delimiter -> a HIGH escalation signal, never the sole gate). validate_for_store(mode) applies policy: off (no-op) | log (judge+flag, never blocks) | strip (neutralize URLs/code-fences in the stored text) | reject (drop a HIGH-severity fact). Judge path is flag-gated ([pgvector].memguard_judge_mode, default "model"); when the micro lane is unavailable it DEGRADES to the structural verdict (fail-safe: an obvious control-token still escalates, benign content still stores -- never the deleted keyword gate, never a silent drop of the user's own answer). FAIL-OPEN on a guard bug: a scanner/judge error never blocks a store. server.py owns wiring this before _store_knowledge_task writes + the SSOT policy mode; this is the testable policy in the mios_pdp/mios_sandbox sibling style.
AI-related: ./server.py, ./mios_knowledge.py, ./mios_config.py, ./mios_jsonsalvage.py, /usr/share/mios/mios.toml, ./test_mios_memguard.py
AI-functions: scan_fact, _judge_severity, _judge_mode, validate_for_store, _neutralize

<!-- mios-src:3b5076801d08 from usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py:1-3 -->


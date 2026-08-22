<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Anti-fabrication POLISH/VERITY cluster extracted verbatim from server.py (refactor R6 wave). Three functions: _verity_factcheck (generate up to N SearXNG queries for a draft's UNCERTAIN specifics, run quick fresh searches, return a CONFIRM/DROP fact-check block -- gated to web turns), _strip_ungrounded_figures (deterministic output-side guard dropping sentences whose $-price/N%-percent figures are absent from the haystack polish saw, with a >half-the-figures fail-safe and abbreviation-protected sentence split), and polish_response (final sub-agent->user answer re-shaper grounded in tool-history + satisfaction verdicts + web sources + the verity fact-check; language-anchored to the operator's ORIGINAL words; appends the figure-guard, the ASK-TO-RUN proposal block, and the GLOBAL clarification block; fire-and-forget knowledge-store + SKILL.md mirror). Config-style constants (REFINE_*/POLISH_*/WEB_RESEARCH_SEARCH_TIMEOUT/_WEB_ENRICH_VERBS/ASK_CLARIFY_JUDGE_ENABLE/_POLISH_SYSTEM) and the server-side runtime helpers (_polish_post, _recent_tool_history, _format_tool_history, _recent_satisfaction_verdicts, _format_satisfaction_block, _store_knowledge, _write_skill_md_fire, _proposal_var) are dependency-INJECTED via configure() (one-way boundary -- mios_verity NEVER imports server). The generative clarification judge _clarify_question (the GLOBAL clarification block's gate) lives here too -- it reads only mios_config model-call scalars (ROUTER_MODEL/PLANNER_ENDPOINT/PLANNER_TIMEOUT_S) + _loads_lenient, so it moved home (no longer injected). _loads_lenient (mios_jsonsalvage) and _env_grounding (mios_grounding) are imported directly. server.py re-imports every name under its EXACT original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_grounding.py, ./test_mios_verity.py
AI-functions: _verity_factcheck, _strip_ungrounded_figures, polish_response, _clarify_question, configure

<!-- mios-src:8242cfc90d87 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py:1-3 -->


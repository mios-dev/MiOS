<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_quota -- per-user quota + rate limiting (WS-6, the...

mios_quota -- per-user quota + rate limiting (WS-6, the AIOS multi-tenant
fairness layer).

Pure stdlib. RESEARCH NOTE: the production pattern for an LLM gateway (LiteLLM
per-key budgets + RPM/TPM limits) is a PER-PRINCIPAL request-rate cap plus a
spend budget over a rolling window. This is that tracker: a sliding-window RPM
limiter + a per-window cost budget, per user. server.py keys it on the verified
principal (WS-A10) and persists the spend; this owns the deterministic decision.

limits <= 0 disable that dimension -> a user with no [users.*] quota (the
single-user default) is unlimited, so this is a zero-behaviour-change default.

Sources: LiteLLM per-key budgets + rate limiting / cost tracking (docs.litellm.ai).

<!-- mios-src:cc5d12fd8551 from usr/lib/mios/agent-pipe/mios_pipe/access/quota.py:3-16 -->

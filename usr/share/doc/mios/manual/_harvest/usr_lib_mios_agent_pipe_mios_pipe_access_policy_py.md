<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: RBAC/PDP/quota + human-in-the-loop POLICY plane extracted verbatim from server.py (refactor R7 security wave). The least-privilege + approval-gate decision helpers: the #55 risk lattice (_PERMISSION_TIERS / _perm_rank), the effective-tier resolver (_effective_perm, recipe-aware), the #62 HITL block-reason + out-of-process arbiter (_hitl_block_reason / _hitl_arbiter_verdict, off by default), the per-AGENT and per-USER capability surface filters (_agent_rbac_filter / _user_rbac_filter via the shared mios_pdp core, fail-closed on unknown max_permission), the principal resolver (_match_user_cfg), the WS-6 per-user quota gate (_quota_for / _dispatch_quota_reason), and the WS-A9 dispatch-time PDP (_dispatch_pdp_reason). Gates are NAME-KEYED on verb keys + permission tiers -- never rename a verb key, gate name, or tier. mios_pdp (as _pdp) + mios_quota are imported direct; _toml_section comes from mios_config; every server symbol they touch (the verb/recipe catalogs, _AGENT_REGISTRY, the HITL/client/dispatch ContextVars, _pending_hash, _get_client, the DB-event helpers) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_pdp.py, ./mios_quota.py, ./mios_secset.py, ./test_mios_policy.py
AI-functions: quota_preload, _quota_load, _quota_save, _quota_hydrate, _quota_persist, _perm_rank, _effective_perm, _hitl_block_reason, _hitl_arbiter_verdict, _agent_rbac_filter, _match_user_cfg, _user_rbac_filter, _quota_for, _dispatch_quota_reason, _dispatch_pdp_reason, configure

<!-- mios-src:04e632d816ba from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:1-3 -->


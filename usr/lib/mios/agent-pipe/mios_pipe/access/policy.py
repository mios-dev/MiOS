# AI-hint: RBAC/PDP/quota + human-in-the-loop POLICY plane extracted verbatim from server.py (refactor R7 security wave). The least-privilege + approval-gate decision helpers: the #55 risk lattice (_PERMISSION_TIERS / _perm_rank), the effective-tier resolver (_effective_perm, recipe-aware), the #62 HITL block-reason + out-of-process arbiter (_hitl_block_reason / _hitl_arbiter_verdict, off by default), the per-AGENT and per-USER capability surface filters (_agent_rbac_filter / _user_rbac_filter via the shared mios_pdp core, fail-closed on unknown max_permission), the principal resolver (_match_user_cfg), the WS-6 per-user quota gate (_quota_for / _dispatch_quota_reason), and the WS-A9 dispatch-time PDP (_dispatch_pdp_reason). Gates are NAME-KEYED on verb keys + permission tiers -- never rename a verb key, gate name, or tier. mios_pdp (as _pdp) + mios_quota are imported direct; _toml_section comes from mios_config; every server symbol they touch (the verb/recipe catalogs, _AGENT_REGISTRY, the HITL/client/dispatch ContextVars, _pending_hash, _get_client, the DB-event helpers) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_pdp.py, ./mios_quota.py, ./mios_secset.py, ./test_mios_policy.py
# AI-functions: _perm_rank, _effective_perm, _hitl_block_reason, _hitl_arbiter_verdict, _agent_rbac_filter, _match_user_cfg, _user_rbac_filter, _quota_for, _dispatch_quota_reason, _dispatch_pdp_reason, configure
"""RBAC / PDP / quota + human-in-the-loop policy decision plane.

Extracted verbatim from ``server.py``. Holds the least-privilege capability
gate (the #55 risk lattice + per-agent/per-user surface filters routed through
the shared :mod:`mios_pdp` core), the #62 human-in-the-loop block-reason + the
out-of-process policy arbiter, the WS-6 per-user quota gate, and the WS-A9
dispatch-time Policy Decision Point.

SECURITY-CRITICAL: the gates are NAME-KEYED on verb keys and permission tiers.
The moved bodies are byte-identical to the originals -- no verb key, gate name,
permission tier, or set-membership test was renamed or rewritten. ``mios_pdp``
(aliased ``_pdp``) and ``mios_quota`` are imported directly; ``_toml_section``
comes from :mod:`mios_config`; every other server-side symbol these helpers
touch (the verb / recipe catalogs, the agent registry, the HITL / client /
dispatch ContextVars, ``_pending_hash``, ``_get_client`` and the DB-event
helpers) is injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``). ``server.py`` re-imports every name under its
original alias so the module's public surface is byte-identical.
"""

from __future__ import annotations

import contextvars  # noqa: F401 -- referenced in injected ContextVar type hints
import logging
import time
from typing import Optional

import mios_pdp as _pdp   # WS-A9 policy decision point (capability gate)
import mios_quota         # WS-6 per-user quota / rate-limit (inert until configured)
import mios_hitl          # the shared HITL verdict resolver (mios_hitl.decide) both gates route through
from mios_config import _toml_section   # layered mios.toml SSOT reader

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# The policy helpers read server.py's verb/recipe catalogs, the agent registry,
# the HITL / client-env / dispatch-agent ContextVars, the ask-to-run action
# hasher, the shared httpx client factory and the DB-event helpers. server.py
# calls configure() with those AFTER every one is defined (one-way boundary:
# this module never imports server). The placeholders below carry the documented
# defaults so a standalone ``import mios_policy`` still succeeds; every consumer
# is runtime (per-request) so nothing fires before configure() runs.

# mutable catalogs / registry (injected BY REFERENCE -- server assigns each
# exactly once; _AGENT_REGISTRY is re-injected on a live membership reload)
_VERB_CATALOG: dict = {}
_RECIPE_CATALOG: dict = {}
_AGENT_REGISTRY: dict = {}

# ContextVars (injected by reference -- shared live objects)
_hitl_approved_var = None
_hitl_blocked_var = None
_client_env_var = None
_dispatch_agent_var = None

# server-side helpers (injected)
_pending_hash = None
_get_client = None
_db_fire = None
_db_post = None
_db_create = None


def configure(*, verb_catalog=None, recipe_catalog=None, agent_registry=None,
              hitl_approved_var=None, hitl_blocked_var=None, client_env_var=None,
              dispatch_agent_var=None, pending_hash=None, get_client=None,
              db_fire=None, db_post=None, db_create=None) -> None:
    """Inject server.py's catalogs, registry, ContextVars and runtime helpers the
    RBAC/PDP/quota/HITL policy helpers call back into. Idempotent; every arg is
    optional so a membership reload can re-inject just ``agent_registry``."""
    global _VERB_CATALOG, _RECIPE_CATALOG, _AGENT_REGISTRY
    global _hitl_approved_var, _hitl_blocked_var, _client_env_var
    global _dispatch_agent_var, _pending_hash, _get_client
    global _db_fire, _db_post, _db_create
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if recipe_catalog is not None:
        _RECIPE_CATALOG = recipe_catalog
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if hitl_approved_var is not None:
        _hitl_approved_var = hitl_approved_var
    if hitl_blocked_var is not None:
        _hitl_blocked_var = hitl_blocked_var
    if client_env_var is not None:
        _client_env_var = client_env_var
    if dispatch_agent_var is not None:
        _dispatch_agent_var = dispatch_agent_var
    if pending_hash is not None:
        globals()["_pending_hash"] = pending_hash
    if get_client is not None:
        globals()["_get_client"] = get_client
    if db_fire is not None:
        globals()["_db_fire"] = db_fire
    if db_post is not None:
        globals()["_db_post"] = db_post
    if db_create is not None:
        globals()["_db_create"] = db_create


# #55 risk lattice for the per-agent capability gate. The tiers ARE the SSOT
# permission vocabulary documented in mios.toml ("permission -- read | write |
# interactive"), ordered lowest->highest risk. Declarative + SSOT-tunable via
# [ai].permission_tiers -- never a hardcoded keyword test against user content.
_PERMISSION_TIERS = [
    str(t).strip().lower()
    for t in ((_toml_section("ai") or {}).get("permission_tiers") or [])
    if str(t).strip()
]


def _perm_rank(perm: str) -> int:
    """Risk rank of a permission tier (lower index = safer). A tier not in the
    lattice ranks ABOVE the top (most restrictive) so an unclassified verb is
    gated rather than silently granted -- fail-closed on the risk axis."""
    p = str(perm or "").strip().lower()
    try:
        return _PERMISSION_TIERS.index(p)
    except ValueError:
        return len(_PERMISSION_TIERS)


# ── #62 WS-9: human-in-the-loop gate-mode ────────────────────────────────────
# SSOT [ai].hitl_mode = off (default) | audit | block, applied at the single
# dispatch chokepoint (dispatch_mios_verb). It reuses the #55 risk lattice + the
# agent-passport humanInLoop intent: an action whose permission tier is at/above
# [ai].hitl_threshold is "high-risk". off -> no-op (zero overhead, zero behaviour
# change). audit -> LOG every high-risk action + proceed (observe before you
# enforce). block -> REFUSE it deterministically (no execution, no hang) until a
# human approves / the operator allowlists it. Default off so this ships INERT;
# the operator opts in. Degrade-open everywhere: any error -> proceed (a gate bug
# must never spuriously block real work). The out-of-process policy arbiter named
# in #62 is a further step ON TOP of this in-process gate.
_HITL_MODE = str((_toml_section("ai") or {}).get("hitl_mode") or "off").strip().lower()
_HITL_THRESHOLD = str((_toml_section("ai") or {}).get("hitl_threshold")
                      or "interactive").strip().lower()


def _effective_perm(tool: str, args: "Optional[dict]" = None) -> str:
    """The permission tier that actually governs THIS call. Umbrella verbs that
    dispatch to a NAMED sub-action with its own permission (os_recipe -> a named
    [recipes.*]) must be gated by the RECIPE's tier, not the umbrella verb's
    worst-case 'interactive' -- otherwise HITL block-mode neutralizes even the
    read-only recipes (service-status / show-network / disk-usage / os-control-
    health) the agent needs for routine OS introspection. Falls back to the
    verb's own permission. Degrade-open: any lookup miss -> the verb tier."""
    vperm = str((_VERB_CATALOG.get(tool) or {}).get("permission", "read")).lower()
    try:
        if tool == "os_recipe" and args:
            rn = str((args or {}).get("name") or "").strip().replace("_", "-")
            rc = _RECIPE_CATALOG.get(rn)
            if rc:
                return str(rc.get("permission", vperm)).lower()
    except Exception:  # noqa: BLE001 -- degrade-open
        pass
    return vperm


def _hitl_block_reason(tool: str, args: "Optional[dict]" = None) -> "Optional[str]":
    """#62: the [ai] RISK-TIER half of the HITL decision. In BLOCK mode return a
    human-readable refusal reason if `tool`'s effective tier is at/above
    [ai].hitl_threshold; AUDIT logs + proceeds (None); OFF is inert (None). The
    block/observe verdict is computed by the SINGLE shared resolver
    (``mios_hitl.decide``) that the [hitl] verb-scope gate also routes through, so the
    two HITL gates can no longer disagree (the stricter-wins / fail-safe combine lives
    in the resolver). Degrade-open: never raises, never gates on error. For os_recipe
    the effective tier is the NAMED recipe's, not the umbrella verb's."""
    if _HITL_MODE not in ("audit", "block"):
        return None
    try:
        # ask-to-run: if the user EXPLICITLY approved THIS exact action this turn
        # (hash match), let it run -- the proposal they confirmed. Scoped to the one
        # hashed action; every other high-tier action is still gated as before.
        _appr = _hitl_approved_var.get()
        if _appr and _appr == _pending_hash(tool, args or {}):
            return None
        vperm = _effective_perm(tool, args)
        in_tier = _perm_rank(vperm) >= _perm_rank(_HITL_THRESHOLD)
        verdict = mios_hitl.decide(in_tier_scope=in_tier, ai_mode=_HITL_MODE)
        if verdict == mios_hitl.OBSERVE:
            # audit mode (tier scope): observe-only -- log + proceed, as before.
            log.info("HITL audit: %s (tier=%s >= %s) WOULD require approval -- "
                     "proceeding (audit mode)", tool, vperm, _HITL_THRESHOLD)
            return None
        if verdict != mios_hitl.BLOCK:
            return None  # below the gate threshold -> not human-gated
        log.info("HITL block: refused %s (tier=%s) pending human approval", tool, vperm)
        # record the block turn-scoped so the final answer can flag it honestly
        try:
            _bl = _hitl_blocked_var.get()
            if not isinstance(_bl, list):
                _bl = []
                _hitl_blocked_var.set(_bl)
            if tool not in _bl:
                _bl.append(tool)
        except Exception:  # noqa: BLE001
            pass
        return (f"'{tool}' is a {vperm}-tier action and HITL block-mode is ON: it "
                f"needs explicit human approval before running, so it was NOT "
                f"executed. Approve it, or set [ai].hitl_mode to audit/off, to proceed.")
    except Exception:  # noqa: BLE001 -- degrade-open: a gate bug never blocks work
        return None


# #62 (remaining half) -- OUT-OF-PROCESS policy arbiter. When [ai].hitl_arbiter_url
# is set, a high-risk action is POSTed to that external arbiter for an allow/deny
# verdict on top of the in-process gate. Default unset -> the helper returns None
# instantly (no HTTP, no overhead, no behaviour change). Degrade-open per
# [ai].hitl_arbiter_fail (default 'open': a down/erroring arbiter PROCEEDS; set
# 'closed' to fail-safe-deny). Short timeout so a slow arbiter never hangs dispatch.
_HITL_ARBITER_URL = str((_toml_section("ai") or {}).get("hitl_arbiter_url") or "").strip()
_HITL_ARBITER_FAIL = str((_toml_section("ai") or {}).get("hitl_arbiter_fail")
                         or "open").strip().lower()


async def _hitl_arbiter_verdict(tool: str, args: dict) -> "Optional[str]":
    """Consult the external policy arbiter for a high-risk action; return a refusal
    reason on DENY, else None (allow/not-applicable). No-op when no arbiter URL is
    configured. Degrade-open per _HITL_ARBITER_FAIL."""
    if not _HITL_ARBITER_URL:
        return None
    try:
        vperm = _effective_perm(tool, args)
        if _perm_rank(vperm) < _perm_rank(_HITL_THRESHOLD):
            return None  # below the threshold -> arbiter not consulted
        client = await _get_client()
        r = await client.post(
            _HITL_ARBITER_URL,
            json={"verb": tool, "tier": vperm, "args": args},
            timeout=5.0)
        if r.status_code == 200:
            v = r.json() if r.content else {}
            if isinstance(v, dict) and not v.get("allow", True):
                log.info("HITL arbiter: DENY %s (tier=%s): %s",
                         tool, vperm, v.get("reason"))
                return str(v.get("reason") or f"'{tool}' denied by the policy arbiter.")
            return None  # explicit allow (or no verdict field) -> proceed
        if _HITL_ARBITER_FAIL == "closed":
            return (f"'{tool}' blocked: policy arbiter returned HTTP {r.status_code} "
                    f"(fail-closed).")
        return None
    except Exception as e:  # noqa: BLE001 -- degrade-open
        log.warning("HITL arbiter unreachable for %s: %s", tool, e)
        if _HITL_ARBITER_FAIL == "closed":
            return f"'{tool}' blocked: policy arbiter unreachable (fail-closed)."
        return None


def _agent_rbac_filter(aname: str, tools: list) -> list:
    """WS-2 per-agent RBAC + #55 capability/risk gate: restrict a dispatched
    agent's tool surface to what its role is permitted. SSOT:
    [agents.<name>].denied_verbs / .allowed_verbs / .max_permission in mios.toml
    (layered vendor<etc<user, surfaced via _AGENT_REGISTRY). No-op when none is
    set -> ZERO behaviour change. Only gates BARE VERBS (names in _VERB_CATALOG):
    names in denied_verbs are dropped; if allowed_verbs is set, any verb NOT in it
    is dropped; if max_permission is set, any verb whose permission tier outranks
    it is dropped. Non-verb tools (recipes/skills/MCP/client tools) pass through
    untouched unless explicitly named in denied_verbs."""
    if not aname or not tools:
        return tools
    cfg = _AGENT_REGISTRY.get(aname) or {}
    denied = {str(v) for v in (cfg.get("denied_verbs") or [])}
    allowed = {str(v) for v in (cfg.get("allowed_verbs") or [])}
    # WS-A9: route the ceiling + per-tool decision through the shared PDP core
    # (mios_pdp) so the surface filter and the dispatch-time gate can NEVER
    # diverge. resolve_ceiling FAILS CLOSED on an unknown max_permission (a typo
    # used to fall OPEN -> full surface). Verb permission defaults to "read".
    max_perm = str(cfg.get("max_permission") or "").strip().lower()
    ceiling = _pdp.resolve_ceiling(max_perm, _PERMISSION_TIERS)
    if not denied and not allowed and ceiling is None:
        return tools
    out = []
    for t in tools:
        nm = ((t.get("function") or {}).get("name") if isinstance(t, dict) else "") or ""
        vperm = str((_VERB_CATALOG.get(nm) or {}).get("permission", "read")).lower()
        if _pdp.decide(nm, in_catalog=nm in _VERB_CATALOG, verb_perm=vperm,
                       denied=denied, allowed=allowed, ceiling_rank=ceiling,
                       tiers=_PERMISSION_TIERS).allow:
            out.append(t)
    if len(out) != len(tools):
        log.info("agent RBAC: %s surface %d -> %d (denied=%d allowed=%d max_perm=%s)",
                 aname, len(tools), len(out), len(denied), len(allowed),
                 max_perm or "-")
    return out


def _match_user_cfg() -> tuple:
    """WS-6/WS-A9: resolve the [users.<name>] policy for the CURRENT request's
    principal (the surface-claimed user_name/user_email in _client_env_var).
    Returns (label, cfg) or ("", None) when no entry matches. Shared by the
    user-axis surface filter AND the dispatch-time PDP so both enforce ONE policy
    (surface and dispatch can never diverge)."""
    env = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
    uname = str((env or {}).get("user_name") or "").strip().lower()
    uemail = str((env or {}).get("user_email") or "").strip().lower()
    if not uname and not uemail:
        return "", None
    users = _toml_section("users") or {}
    if not isinstance(users, dict) or not users:
        return "", None
    for k, v in users.items():
        if not isinstance(v, dict):
            continue
        kk = str(k).strip().lower()
        _vemail = str(v.get("email", "")).strip().lower()
        # Guard the email arm with `uemail and ...`: an empty-email entry must not
        # spuriously match an empty-email user; the key must be non-empty too.
        if (kk and kk in (uname, uemail)) or (uemail and _vemail == uemail):
            return (uname or uemail), v
    return "", None


def _user_rbac_filter(tools: list) -> list:
    """#60 WS-6 per-USER authz: restrict the dispatched tool surface by WHO the
    request is from -- the per-USER axis, complementing _agent_rbac_filter's
    per-AGENT axis. SSOT: [users.<name>].denied_verbs / .allowed_verbs /
    .max_permission in mios.toml, matched to the principal the chat surface
    forwarded (_client_env user_name / user_email). No-op when no [users.*] entry
    matches the current user -> ZERO behaviour change (default; single-user MiOS is
    unaffected). Same verb-gating semantics + risk lattice as #55.

    SCOPE NOTE: this keys on the surface-CLAIMED identity. Cryptographic
    SIGNED-principal verification (the 'signed principal' half of #60) is a further
    step -- until then this is policy over a TRUSTED-surface identity, not an auth
    boundary against a forged caller."""
    if not tools:
        return tools
    label, cfg = _match_user_cfg()
    if not cfg:
        return tools
    denied = {str(v) for v in (cfg.get("denied_verbs") or [])}
    allowed = {str(v) for v in (cfg.get("allowed_verbs") or [])}
    max_perm = str(cfg.get("max_permission") or "").strip().lower()
    ceiling = _pdp.resolve_ceiling(max_perm, _PERMISSION_TIERS)  # WS-A9: fail-closed
    if not denied and not allowed and ceiling is None:
        return tools
    out = []
    for t in tools:
        nm = ((t.get("function") or {}).get("name") if isinstance(t, dict) else "") or ""
        vperm = str((_VERB_CATALOG.get(nm) or {}).get("permission", "read")).lower()
        if _pdp.decide(nm, in_catalog=nm in _VERB_CATALOG, verb_perm=vperm,
                       denied=denied, allowed=allowed, ceiling_rank=ceiling,
                       tiers=_PERMISSION_TIERS).allow:
            out.append(t)
    if len(out) != len(tools):
        log.info("user RBAC: %s surface %d -> %d (denied=%d allowed=%d max_perm=%s)",
                 label, len(tools), len(out), len(denied), len(allowed), max_perm or "-")
    return out


# WS-A9: emit a PDP audit event on ALLOW too when [ai].pdp_audit_allow=true
# (default off -> deny-only auditing, ~zero overhead on the hot allow path).
_PDP_AUDIT_ALLOW = str((_toml_section("ai") or {}).get("pdp_audit_allow")
                       or "").strip().lower() in ("1", "true", "yes", "on")


# ── WS-6 per-user quota / rate-limit (mios_quota) ───────────────────────────
# Per-user QuotaTracker cache, built LAZILY from the matched [users.<name>]
# config's rpm_limit / daily_budget. INERT BY DEFAULT: a user with no quota keys
# (the single-user MiOS default) -> _quota_for returns None -> the dispatch quota
# gate is skipped entirely (one dict lookup), so behaviour is unchanged until an
# operator adds limits. server.py owns this wiring; mios_quota owns the decision.
_QUOTA_TRACKERS: dict = {}


def _quota_for(ulabel: str, ucfg: dict):
    """Return the QuotaTracker for a user, or None when that user has no limits
    configured (rpm_limit/daily_budget both <= 0 -> unlimited -> skip)."""
    rpm = int((ucfg or {}).get("rpm_limit", 0) or 0)
    budget = float((ucfg or {}).get("daily_budget", 0) or 0.0)
    if rpm <= 0 and budget <= 0:
        return None
    tr = _QUOTA_TRACKERS.get(ulabel)
    if tr is None:
        tr = mios_quota.QuotaTracker(rpm_limit=rpm, daily_budget=budget)
        _QUOTA_TRACKERS[ulabel] = tr
    return tr


def _dispatch_quota_reason(verb: str) -> "Optional[str]":
    """WS-6 per-user rate/budget gate at the dispatch chokepoint. Counts one
    request per verb dispatch for the matched [users.*] principal; DENY when over
    the user's rpm_limit / daily_budget. Returns a refusal reason on deny, else
    None. INERT when the principal has no quota config (the default), and
    degrade-open (a quota bug must never block real work)."""
    try:
        ulabel, ucfg = _match_user_cfg()
        if not ucfg:
            return None
        tr = _quota_for(ulabel, ucfg)
        if tr is None:
            return None
        v = tr.check(ulabel, time.time())
        if not v.allowed:
            return (f"quota exceeded for user '{ulabel}' ({v.reason}); "
                    f"'{verb}' was NOT executed.")
        return None
    except Exception:  # noqa: BLE001 -- degrade-open: a quota bug never blocks work
        return None


def _dispatch_pdp_reason(verb: str) -> "Optional[str]":
    """WS-A9 dispatch-time Policy Decision Point. Re-checks the per-AGENT
    (_dispatch_agent_var) and per-USER (_match_user_cfg) capability policy for
    `verb` at the SINGLE dispatch chokepoint, through the SAME mios_pdp core the
    surface filters use -- so a verb pruned from the model surface (or named by a
    stale/MCP/A2A/fabricated call) can NOT still dispatch (the RBAC bypass WS-A9
    closes). Returns a refusal reason on DENY, else None. Degrade-open: an
    unexpected error proceeds (a PDP bug must never block real work); an EXPLICIT
    policy deny always blocks."""
    try:
        in_cat = verb in _VERB_CATALOG
        vperm = str((_VERB_CATALOG.get(verb) or {}).get("permission", "read")).lower()
        checks = []
        aname = (_dispatch_agent_var.get() or "").strip()
        if aname:
            checks.append((f"agent '{aname}'", _AGENT_REGISTRY.get(aname) or {}))
        ulabel, ucfg = _match_user_cfg()
        if ucfg:
            checks.append((f"user '{ulabel}'", ucfg))
        for who, cfg in checks:
            d = _pdp.decide(
                verb, in_catalog=in_cat, verb_perm=vperm,
                denied={str(v) for v in (cfg.get("denied_verbs") or [])},
                allowed={str(v) for v in (cfg.get("allowed_verbs") or [])},
                ceiling_rank=_pdp.resolve_ceiling(
                    str(cfg.get("max_permission") or ""), _PERMISSION_TIERS),
                tiers=_PERMISSION_TIERS)
            if not d.allow:
                return (f"'{verb}' is not permitted for {who} ({d.rule}): "
                        f"{d.reason}. It was NOT executed.")
            if _PDP_AUDIT_ALLOW:
                _db_fire(_db_post(_db_create("event", {
                    "source": "agent-pipe", "kind": "pdp_allow", "severity": "info",
                    "summary": f"PDP allow {verb} for {who}",
                    "payload": {"verb": verb, "who": who, "rule": d.rule},
                }, now_fields=("ts",))))
        return None
    except Exception:  # noqa: BLE001 -- degrade-open: a PDP bug never blocks work
        return None

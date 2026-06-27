# AI-hint: Stdlib assert-script for mios_policy (R7 security wave). Proves the
# least-privilege capability gate + HITL block plane behaves correctly against
# synthetic agent/verb configs: _perm_rank tier ordering (read<write<interactive),
# _effective_perm recipe-aware resolution, _agent_rbac_filter allow/deny, the
# WS-A9 _dispatch_pdp_reason gate, and the #62 _hitl_block_reason refusal in
# block-mode. A silent gate-disable is the worst regression -- these assertions
# fail loudly if a tainted/high-priv verb stops being blocked.
# AI-related: ./mios_policy.py, ./mios_pdp.py
"""Standalone test: python test_mios_policy.py (exit 0 = pass)."""

import contextvars

import mios_policy


# -- synthetic dependency injection (no server.py) ------------------
_dispatch_agent_var = contextvars.ContextVar("dispatch_agent", default="")
_client_env_var = contextvars.ContextVar("client_env", default=None)
_hitl_approved_var = contextvars.ContextVar("hitl_approved", default=None)
_hitl_blocked_var = contextvars.ContextVar("hitl_blocked", default=None)

_VERB_CATALOG = {
    "web_search": {"permission": "read"},
    "create_file": {"permission": "write"},
    "powershell_run": {"permission": "interactive"},
    "os_recipe": {"permission": "interactive"},
}
_RECIPE_CATALOG = {
    "service-status": {"permission": "read"},
}
_AGENT_REGISTRY = {
    "researcher": {"denied_verbs": ["powershell_run"]},
    "readonly": {"max_permission": "read"},
}

mios_policy.configure(
    verb_catalog=_VERB_CATALOG,
    recipe_catalog=_RECIPE_CATALOG,
    agent_registry=_AGENT_REGISTRY,
    hitl_approved_var=_hitl_approved_var,
    hitl_blocked_var=_hitl_blocked_var,
    client_env_var=_client_env_var,
    dispatch_agent_var=_dispatch_agent_var,
    pending_hash=lambda tool, args: "stub-hash",
    get_client=lambda: None,
    db_fire=lambda *a, **k: None,
    db_post=lambda *a, **k: None,
    db_create=lambda *a, **k: None,
)


def _tool(name):
    return {"type": "function", "function": {"name": name}}


# -- 1. _perm_rank ordering: read < write < interactive -------------
r_read = mios_policy._perm_rank("read")
r_write = mios_policy._perm_rank("write")
r_inter = mios_policy._perm_rank("interactive")
assert r_read < r_write < r_inter, (r_read, r_write, r_inter)
# an unclassified tier ranks ABOVE the top (fail-closed on the risk axis)
assert mios_policy._perm_rank("nonsense-tier") > r_inter
print("ok  _perm_rank read<write<interactive + unknown fail-closed")


# -- 2. _effective_perm resolution (verb + recipe-aware) ------------
assert mios_policy._effective_perm("web_search") == "read"
assert mios_policy._effective_perm("powershell_run") == "interactive"
# os_recipe umbrella resolves to the NAMED recipe's tier, not the umbrella's
assert mios_policy._effective_perm("os_recipe", {"name": "service_status"}) == "read"
# unknown recipe falls back to the umbrella verb's tier
assert mios_policy._effective_perm("os_recipe", {"name": "no-such"}) == "interactive"
print("ok  _effective_perm verb + recipe-aware resolution")


# -- 3. _agent_rbac_filter allow/deny on a synthetic agent cfg ------
surface = [_tool("web_search"), _tool("create_file"), _tool("powershell_run")]
filtered = mios_policy._agent_rbac_filter("researcher", surface)
fnames = {t["function"]["name"] for t in filtered}
assert "powershell_run" not in fnames, fnames  # denied verb dropped
assert "web_search" in fnames and "create_file" in fnames, fnames  # safe verbs kept
# max_permission=read ceiling drops write+interactive, keeps read
ro = mios_policy._agent_rbac_filter("readonly", surface)
ronames = {t["function"]["name"] for t in ro}
assert ronames == {"web_search"}, ronames
# unknown agent -> no-op (full surface)
assert len(mios_policy._agent_rbac_filter("ghost", surface)) == len(surface)
print("ok  _agent_rbac_filter denied/ceiling drop + safe pass-through")


# -- 4. _dispatch_pdp_reason gate (the WS-A9 RBAC bypass close) ------
def _as_agent(name, fn):
    ctx = contextvars.copy_context()
    return ctx.run(lambda: (_dispatch_agent_var.set(name), fn())[1])


# a denied high-priv verb is BLOCKED at dispatch even if it bypassed the surface
blocked = _as_agent("researcher", lambda: mios_policy._dispatch_pdp_reason("powershell_run"))
assert blocked is not None and "powershell_run" in blocked, blocked
# a safe verb is ALLOWED
allowed = _as_agent("researcher", lambda: mios_policy._dispatch_pdp_reason("web_search"))
assert allowed is None, allowed
# no agent context -> agent-axis PDP is a no-op (user-axis only; none configured)
assert mios_policy._dispatch_pdp_reason("powershell_run") is None
print("ok  _dispatch_pdp_reason blocks denied / allows safe / no-op off-agent")


# -- 5. _hitl_block_reason refusal in block-mode (#62) --------------
# flip the module gate-mode to block for this assertion (default off ships inert)
mios_policy._HITL_MODE = "block"
mios_policy._HITL_THRESHOLD = "interactive"
try:
    reason = mios_policy._hitl_block_reason("powershell_run")
    assert reason is not None and "powershell_run" in reason, reason  # high-tier blocked
    assert mios_policy._hitl_block_reason("web_search") is None  # below threshold proceeds
finally:
    mios_policy._HITL_MODE = "off"
print("ok  _hitl_block_reason blocks interactive / passes read in block-mode")


print("\nALL mios_policy tests passed")

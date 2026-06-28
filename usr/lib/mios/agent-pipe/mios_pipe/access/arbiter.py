# AI-hint: WS-9 out-of-process policy-arbiter DECISION core. Pure-stdlib verdict logic the mios-policy-arbiter service uses to answer the agent-pipe's HITL arbiter client (_hitl_arbiter_verdict POSTs {verb,tier,args} -> {allow,reason}). decide() applies an explicit deny-list (always refuse), an allow-list (when set, only these auto-allow), and a risk-tier ceiling (verbs at/above arbiter_block_tier are refused) -- a SECOND, out-of-process opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP, so dangerous-verb policy can be changed/owned without redeploying the agent-pipe. The service wrapper owns HTTP + config load; this module is pure so it unit-tests in isolation.
# AI-related: ./server.py, /usr/libexec/mios/mios-policy-arbiter, /usr/lib/systemd/system/mios-policy-arbiter.service, /usr/share/mios/mios.toml, ./mios_pdp.py, ./test_mios_arbiter.py
# AI-functions: decide, class Verdict
"""mios_arbiter -- the MiOS out-of-process policy-arbiter decision core (WS-9).

Pure stdlib. The agent-pipe already has a HITL arbiter CLIENT
(_hitl_arbiter_verdict) that POSTs a high-risk action to an external arbiter for
an allow/deny verdict -- but no arbiter SERVICE existed. This is the decision
logic that service runs: a deterministic, auditable second opinion that the
operator can own/change independently of the agent-pipe.

Policy (first match wins):
  1. verb in deny  -> DENY (always; the hard floor)
  2. allow set AND verb in allow -> ALLOW
  3. allow set AND verb NOT in allow -> DENY (allow-list is exclusive)
  4. tier rank >= block_tier rank -> DENY (risk ceiling)
  5. otherwise -> ALLOW
Fail-closed inputs (an unknown tier ranks above the top) keep an unclassified
high-risk verb gated rather than waved through.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence


class Verdict:
    __slots__ = ("allow", "reason", "rule")

    def __init__(self, allow: bool, reason: str = "", rule: str = "ok") -> None:
        self.allow = bool(allow)
        self.reason = str(reason)
        self.rule = str(rule)

    def to_dict(self) -> dict:
        return {"allow": self.allow, "reason": self.reason, "rule": self.rule}


def _rank(tier: str, tiers: Sequence[str]) -> int:
    t = [str(x).strip().lower() for x in tiers]
    p = str(tier or "").strip().lower()
    try:
        return t.index(p)
    except ValueError:
        return len(t)   # unknown tier -> most restrictive (fail-closed)


def decide(verb: str, tier: str, *,
           deny: Iterable[str] = (), allow: Optional[Iterable[str]] = None,
           block_tier: str = "", tiers: Sequence[str] = ("read", "write", "interactive")) -> Verdict:
    """Return an allow/deny Verdict for one (verb, tier). See module docstring
    for the rule order. `allow=None` means no allow-list (rule 2/3 skipped);
    `allow=[]` (empty list) is an exclusive allow-list that denies everything."""
    v = str(verb or "")
    deny_s = {str(x).strip() for x in (deny or []) if str(x).strip()}
    if v in deny_s:
        return Verdict(False, f"'{v}' is on the arbiter deny-list", "deny_list")
    if allow is not None:
        allow_s = {str(x).strip() for x in allow if str(x).strip()}
        if v in allow_s:
            return Verdict(True, "", "allow_list")
        return Verdict(False, f"'{v}' is not on the arbiter allow-list", "allow_list")
    bt = str(block_tier or "").strip().lower()
    if bt:
        if _rank(tier, tiers) >= _rank(bt, tiers):
            return Verdict(False,
                           f"'{v}' ({tier}-tier) is at/above the arbiter block tier '{bt}'",
                           "block_tier")
    return Verdict(True, "", "ok")

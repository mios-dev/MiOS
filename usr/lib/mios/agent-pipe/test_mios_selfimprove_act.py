# AI-hint: Standalone unit test for mios_selfimprove_act (T-062 ACT + T-064 proof-of-utility decision core): structural anti-reward-hacking isolation (improvable allowed / protected denied / deny-wins / empty-degrade-closed), proposal shape validation, the Autodata solver-gap discriminative signal + eval curation, the pass^k reliability score, the proof-of-utility non-regression gate (margin + require-improvement), and decide_proposal composing them so a proposal targeting the protected evaluator surface is rejected BEFORE it is ever scored. Pure stdlib + the two sibling modules (mios_selfimprove_act / mios_bench) -- no server.py / DB / live models. Surfaces/ids are synthetic non-dictionary tokens so the test proves STRUCTURAL set-membership, never an English/keyword match.
# AI-related: mios_selfimprove_act, mios_bench
# AI-functions: _check, t_isolation, t_validate, t_gap, t_curate, t_passhatk, t_proof, t_decide, main
"""Standalone unit test for mios_selfimprove_act (T-062/T-064 ACT decision core).

Pure stdlib + the sibling modules only -- no server.py / DB / live models. Proves
the ACT half (a) STRUCTURALLY isolates the evaluator/eval/lane-config from a
proposal (anti-reward-hacking), (b) curates eval tasks by the solver-gap, and
(c) accepts a proposal ONLY when it does not regress the baseline (pass^k), with
isolation enforced before any score is consulted.

Synthetic, non-dictionary surface/id tokens throughout: the improvable/protected
sets are made-up kinds the test supplies, so a PASS proves structural set
membership rather than any baked-in English vocabulary.

Run:  python test_mios_selfimprove_act.py
"""

import sys

import mios_selfimprove_act as A

_RESULTS: list = []

# Synthetic surfaces -- no real-word vocabulary, so the logic under test can only
# be structural set membership (the point of the NO-HARDCODE / no-English-gate law).
_IMPR = ["zq_alpha", "zq_beta"]          # improvable surface (a proposal MAY target)
_PROT = ["zp_guard", "zp_eval"]          # protected surface (the evaluator/eval/lane)


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _prop(kind: str, tid: str = "ztarget1") -> dict:
    """A well-formed proposal envelope with synthetic change/rationale prose."""
    return {"target_kind": kind, "target_id": tid,
            "change": "qqx adjust zz token", "rationale": "qqx because zz"}


def t_isolation() -> None:
    a = A.proposal_target_allowed
    _check("isolation: improvable kind allowed", a("zq_alpha", improvable=_IMPR, protected=_PROT))
    _check("isolation: protected kind denied",
           not a("zp_guard", improvable=_IMPR, protected=_PROT))
    _check("isolation: unknown kind denied",
           not a("zx_other", improvable=_IMPR, protected=_PROT))
    # DENY WINS: a kind in BOTH sets is refused (fail-safe) -- the evaluator can never
    # be edited by adding it to the improvable list.
    _check("isolation: deny wins over allow",
           not a("zq_dup", improvable=["zq_dup"], protected=["zq_dup"]))
    # Empty improvable surface -> nothing allowed (degrade-closed, no hardcoded default).
    _check("isolation: empty improvable -> degrade-closed",
           not a("zq_alpha", improvable=[], protected=_PROT))
    _check("isolation: blank kind denied", not a("", improvable=_IMPR, protected=_PROT))


def t_validate() -> None:
    v = A.validate_proposal
    ok, _ = v(_prop("zq_alpha"), improvable=_IMPR, protected=_PROT)
    _check("validate: well-formed improvable proposal ok", ok)
    ok, why = v("not-a-dict", improvable=_IMPR, protected=_PROT)
    _check("validate: non-dict rejected", (not ok) and why == "not_a_proposal", why)
    ok, why = v({"target_id": "z"}, improvable=_IMPR, protected=_PROT)
    _check("validate: missing kind rejected", (not ok) and why == "missing_target_kind", why)
    ok, why = v({"target_kind": "zq_alpha"}, improvable=_IMPR, protected=_PROT)
    _check("validate: missing id rejected", (not ok) and why == "missing_target_id", why)
    ok, why = v(_prop("zp_eval"), improvable=_IMPR, protected=_PROT)
    _check("validate: protected target rejected",
           (not ok) and why == "target_protected_or_unimprovable", why)


def t_gap() -> None:
    _check("gap: strong-weak", abs(A.solver_gap(0.3, 0.7) - 0.4) < 1e-9)
    _check("gap: discriminative at/above min", A.is_discriminative(0.3, 0.7, gap_min=0.2))
    _check("gap: trivial (both pass) not discriminative",
           not A.is_discriminative(0.95, 0.97, gap_min=0.2))
    _check("gap: impossible (both fail) not discriminative",
           not A.is_discriminative(0.0, 0.05, gap_min=0.2))


def t_curate() -> None:
    cands = [
        {"task": "zt_a", "weak": 0.2, "strong": 0.8},   # gap 0.6 -> kept
        {"task": "zt_b", "weak": 0.9, "strong": 0.95},  # gap 0.05 -> dropped (trivial)
        {"task": "zt_c"},                                 # no score pair -> dropped
    ]
    kept = A.curate_eval(cands, gap_min=0.2)
    kept_tasks = [c["task"] for c in kept]
    _check("curate: keeps only the discriminative task", kept_tasks == ["zt_a"], str(kept_tasks))


def t_passhatk() -> None:
    # All-correct over two tasks at k=2 -> perfect reliability.
    _check("pass^k: all-correct -> 1.0",
           abs(A.pass_hat_k_score([(3, 3), (3, 3)], k=2) - 1.0) < 1e-9)
    # A task that never gets k consistent successes drags the worst-case score below 1.
    s = A.pass_hat_k_score([(3, 3), (3, 1)], k=2)
    _check("pass^k: an inconsistent task lowers reliability", s < 1.0, str(s))


def t_proof() -> None:
    p = A.proof_of_utility
    acc, d = p(0.5, 0.5, margin=0.0)
    _check("proof: flat is non-regressing (accept)", acc and abs(d) < 1e-9)
    acc, d = p(0.6, 0.4, margin=0.0)
    _check("proof: regression rejected", (not acc) and d < 0, str(d))
    acc, _ = p(0.50, 0.45, margin=0.1)
    _check("proof: within margin tolerated", acc)
    acc, _ = p(0.50, 0.38, margin=0.1)
    _check("proof: beyond margin rejected", not acc)
    acc, _ = p(0.5, 0.5, margin=0.0, require_improvement=True)
    _check("proof: require-improvement rejects a no-op", not acc)
    acc, _ = p(0.5, 0.6, margin=0.0, require_improvement=True)
    _check("proof: require-improvement accepts a real gain", acc)


def t_decide() -> None:
    d = A.decide_proposal
    # A protected-target proposal is rejected on ISOLATION even with a perfect score
    # delta -- proving isolation is checked BEFORE (and independent of) scoring.
    v = d(_prop("zp_eval"), baseline_score=0.0, proposed_score=1.0,
          improvable=_IMPR, protected=_PROT)
    _check("decide: protected target rejected before scoring",
           (not v["accept"]) and v["reason"] == "isolation_rejected" and v["delta"] is None,
           str(v))
    v = d(_prop("zq_alpha"), baseline_score=0.5, proposed_score=0.6,
          improvable=_IMPR, protected=_PROT)
    _check("decide: improvable + non-regressing accepted",
           v["accept"] and v["reason"] == "accepted" and v["delta"] > 0, str(v))
    v = d(_prop("zq_alpha"), baseline_score=0.7, proposed_score=0.5,
          improvable=_IMPR, protected=_PROT)
    _check("decide: improvable + regressing rejected (delta logged)",
           (not v["accept"]) and v["reason"] == "regression" and v["delta"] < 0, str(v))


def main() -> int:
    for t in (t_isolation, t_validate, t_gap, t_curate, t_passhatk, t_proof, t_decide):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
